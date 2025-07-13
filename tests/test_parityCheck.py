import pytest

from serial_communication_async import DataParser


@pytest.mark.asyncio
async def test_parity_check():
    # 正常なケース
    assert await DataParser.parity_check(b"A,123,321*B", b"A", b"*", 0) == "00"
    # startText と endText が同じ場合、処理が正しく行われるか
    assert await DataParser.parity_check(b"A*A", b"A", b"A", 0) == "00"
    # 空のlineData
    assert await DataParser.parity_check(b"", b"\x02", b"*", 0) == "00"
    # initialValue に初期値以外を設定
    initial_value = 1
    expected_value = format(initial_value, "02x")
    # startTextとendTextが連続している場合（処理されるデータなし）
    assert (
        await DataParser.parity_check(b"A*B", b"A", b"B", initial_value)
        == expected_value
    )


@pytest.mark.asyncio
async def test_parity_check():
    # startTextがNoneの場合
    assert await DataParser.parity_check(b"ABCDEF", None, b"*", 0) == False

    # endTextが見つからない場合
    assert await DataParser.parity_check(b"ABCDEF", b"A", b"Z", 0) == "00"

    # startTextが見つからない場合
    assert await DataParser.parity_check(b"ABCDEF*", b"X", b"*") == "00"

    # 空のデータ
    assert await DataParser.parity_check(b"", b"A", b"*", 0) == "00"

    # Noneデータ
    assert await DataParser.parity_check(None, b"A", b"*", 0) == False
