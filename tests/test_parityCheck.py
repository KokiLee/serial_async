import pytest

from serial_communication_async import DataParser


@pytest.mark.asyncio
async def test_parity_check():
    # 正常なケース
    assert await DataParser.parity_check("A,123,321*B", b"A", b"*", 0) == "00"
    # startText と endText が同じ場合、処理が正しく行われるか
    assert await DataParser.parity_check("A*A", b"A", b"A", 0) == ""
    # 空のlineData
    assert await DataParser.parity_check("", b"\x02", b"*", 0) == "00"
    # initialValue に初期値以外を設定
    initial_value = 1
    expected_value = format(initial_value ^ ord("*"), "02x")
    assert (
        await DataParser.parity_check("A*B", b"A", b"B", initial_value)
        == expected_value
    )
