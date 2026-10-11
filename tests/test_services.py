from app.services import simplify_debts, split_equally


def test_split_equally_gives_remainder_to_first_people():
    assert split_equally(100, 3) == [34, 33, 33]


def test_split_equally_shares_add_up_to_total():
    for total in (1, 99, 100, 12345):
        for people in (1, 2, 3, 7):
            assert sum(split_equally(total, people)) == total


def test_simplify_debts_trip_example():
    # alice +1700, bob -400, charlie -1300 (in paise: multiply by 100)
    balances = {1: 170000, 2: -40000, 3: -130000}
    payments = simplify_debts(balances)
    assert sorted(payments) == sorted([(3, 1, 130000), (2, 1, 40000)])


def test_simplify_debts_when_everyone_is_even():
    assert simplify_debts({1: 0, 2: 0, 3: 0}) == []
