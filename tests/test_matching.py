import pytest

from mygames.matching import Ownership, group, normalize, play_on

PRIORITY = ["steam", "gog", "epic"]


@pytest.mark.parametrize(
    "a, b",
    [
        ("The Witcher 3: Wild Hunt", "The Witcher 3: Wild Hunt - Game of the Year Edition"),
        ("The Witcher 3: Wild Hunt", "The Witcher® 3: Wild Hunt GOTY"),
        ("The Witcher: Enhanced Edition Director's Cut", "The Witcher: Enhanced Edition"),
        ("Divinity: Original Sin 2", "Divinity: Original Sin 2 - Definitive Edition"),
        ("Batman™: Arkham Knight", "Batman: Arkham Knight"),
        ("Pillars of Eternity", "Pillars of Eternity: Definitive Edition"),
        ("Ori and the Blind Forest", "Ori & the Blind Forest"),
        ("Heroes of Might & Magic 3: Complete", "Heroes of Might and Magic 3 Complete"),
        ("Pokémon", "Pokemon"),
        ("Disco Elysium", "Disco Elysium - The Final Cut"),
        ("Aces of the Luftwaffe – Squadron", "Aces of the Luftwaffe - Squadron Extended Edition"),
        ("Stardew Valley", "STARDEW VALLEY"),
        ("Assassin's Creed® Origins", "Assassins Creed Origins"),
        ("Baldur’s Gate 3", "Baldur's Gate 3"),
    ],
)
def test_same_game(a, b):
    assert normalize(a) == normalize(b)


@pytest.mark.parametrize(
    "a, b",
    [
        ("DOOM", "DOOM (1993)"),
        ("Fallout", "Fallout 2"),
        ("Half-Life", "Half-Life 2"),
        ("Gold Rush", "Rush"),
        ("Fool's Gold", "Fool's"),
        ("Persona 5 Royal", "Persona 5"),
    ],
)
def test_different_games(a, b):
    assert normalize(a) != normalize(b)


def test_edition_word_alone_is_not_stripped_to_nothing():
    assert normalize("Deluxe") == "deluxe"


def rows(*items):
    return [Ownership(p, str(i), t) for i, (p, t) in enumerate(items)]


def test_group_prefers_steam_and_flags_duplicate():
    games = group(
        rows(
            ("gog", "The Witcher 3: Wild Hunt - Game of the Year Edition"),
            ("steam", "The Witcher 3: Wild Hunt"),
            ("epic", "The Witcher 3: Wild Hunt"),
            ("gog", "Stardew Valley"),
        ),
        PRIORITY,
    )
    witcher, stardew = sorted(games, key=lambda g: g.title)[::-1]
    assert witcher.title == "The Witcher 3: Wild Hunt"
    assert witcher.platforms == ["epic", "gog", "steam"]
    assert witcher.is_duplicate
    assert play_on(witcher, PRIORITY) == "steam"
    assert not stardew.is_duplicate
    assert play_on(stardew, PRIORITY) == "gog"


def test_unknown_platforms_rank_after_priority_list():
    games = group(rows(("ubisoft", "Anno 1800"), ("epic", "Anno 1800")), PRIORITY)
    assert play_on(games[0], PRIORITY) == "epic"


def test_alias_merges_and_names_group():
    games = group(
        rows(("steam", "FINAL FANTASY VII"), ("gog", "Final Fantasy 7")),
        PRIORITY,
        aliases={"Final Fantasy 7": "Final Fantasy VII"},
    )
    assert len(games) == 1
    assert games[0].title == "Final Fantasy VII"
    assert games[0].platforms == ["gog", "steam"]


def test_ignore_hides_titles():
    games = group(
        rows(("steam", "Cool Game"), ("steam", "Cool Game Soundtrack")),
        PRIORITY,
        ignore=["cool game soundtrack"],
    )
    assert [g.title for g in games] == ["Cool Game"]
