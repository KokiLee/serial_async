import pytest

from src.serial_communication_async import DataParser, HWT905_TTL_Dataparser


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


@pytest.mark.asyncio
async def test_prity_check_with_real_data():
    test_data = b"UQ\xff\xff\xe3\xff\x06\x08\n\x0b\xa9UR\x00\x00\x00\x00\x00\x00\n\x0b\xbcUS\x94\xfe\x08\x00\xfd\x06\xccF"
    test_data_magnetic = b"UQ'\x00g\xff\x05\x08~\t\xc7UR\x00\x00\xff\xff\x00\x00~\t,US\x1e\xfc=\xff\x17\xd6\xccF\xfdUT\xf6\xfbI\x03\xa1\xf3\x00\x00z"

    result = await DataParser.parity_check(test_data)
    result1 = await DataParser.parity_check(test_data_magnetic)

    assert result is not None
    assert result1 is not None
    assert isinstance(result, str)
    assert isinstance(result1, str)


@pytest.mark.asyncio
def test_protocol_with_multiple_packets():
    test_data = b"UQ\xff\xff\xe3\xff\x06\x08\n\x0b\xa9UR\x00\x00\x00\x00\x00\x00\n\x0b\xbcUS\x94\xfe\x08\x00\xfd\x06\xccF"
    test_data_magnetic = b"UQ'\x00g\xff\x05\x08~\t\xc7UR\x00\x00\xff\xff\x00\x00~\t,US\x1e\xfc=\xff\x17\xd6\xccF\xfdUT\xf6\xfbI\x03\xa1\xf3\x00\x00z"

    angular_result = HWT905_TTL_Dataparser.protocol_angular_output(test_data)
    magnetic_result = HWT905_TTL_Dataparser.protocol_magnetic_field_output(
        test_data_magnetic
    )

    assert angular_result is not None
    assert magnetic_result is not None

    roll, pitch, yaw = angular_result
    direction, magnetic_strength = magnetic_result
    assert -180 <= roll <= 180
    assert -180 <= pitch <= 180
    assert -180 <= yaw <= 180

    assert 0 <= direction <= 360
    assert 0 <= magnetic_strength
