import logging
import math
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler("app.log", maxBytes=6000000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


class HWT905_TTL_Dataparser:
    @staticmethod
    def adjust_angular_async(current_angle, previous_angle):
        """
        Corrected overflow and underflow when angular difference exceeding 180 degree
        :return: corrected angle
        """
        if previous_angle != 0:
            angle_diff = current_angle - previous_angle
            if angle_diff > 180:
                current_angle -= 360
            elif angle_diff < -180:
                current_angle += 360
        return current_angle

    @staticmethod
    def protocol_angular_output(
        data,
    ):  # -> tuple[FixtureFunction[SimpleFixtureFunction, FactoryFixtu...:# -> tuple[FixtureFunction[SimpleFixtureFunction, FactoryFixtu...:# -> tuple[FixtureFunction[SimpleFixtureFunction, FactoryFixtu...:
        previous_roll = 0
        previous_pitch = 0
        previous_yaw = 0
        roll = None
        pitch = None
        yaw = None
        try:
            for i in range(len(data) - 1):
                if data[i] == 0x55 and data[i + 1] == 0x53:  # type: ignore
                    # Byte value: An integer representing a single byte. Example: 85 or 0x55
                    # Byte string: A sequence containing one or more byte values. Example: b"\x55"

                    # Combine as a byte sequence.
                    roll_L_H = bytes([data[i + 2], data[i + 3]])  # type: ignore
                    combined_roll = int.from_bytes(
                        roll_L_H, byteorder="little", signed=True
                    )
                    roll = combined_roll / 32768.0 * 180

                    pitch_L_H = bytes([data[i + 4], data[i + 5]])  # type: ignore
                    combined_pitch = int.from_bytes(
                        pitch_L_H, byteorder="little", signed=True
                    )
                    pitch = combined_pitch / 32768.0 * 180

                    yaw_L_H = bytes([data[i + 6], data[i + 7]])  # type: ignore
                    combined_yaw = int.from_bytes(
                        yaw_L_H, byteorder="little", signed=True
                    )
                    yaw = combined_yaw / 32768.0 * 180

                    # Implemented a solution to correct overflow and underflow in sensor data processing.
                    roll = HWT905_TTL_Dataparser.adjust_angular_async(
                        roll, previous_roll
                    )
                    previous_roll = roll

                    pitch = HWT905_TTL_Dataparser.adjust_angular_async(
                        pitch, previous_pitch
                    )
                    previous_pitch = pitch

                    yaw = HWT905_TTL_Dataparser.adjust_angular_async(yaw, previous_yaw)
                    previous_yaw = yaw

            return roll, pitch, yaw

        except Exception as e:
            logger.error("Data doesn't match")

    @staticmethod
    def protocol_magnetic_field_output(data):
        direction = 0
        magnetic_strength = 0
        for i in range(len(data) - 1):
            if data[i] == 0x55 and data[i + 1] == 0x54:  # type: ignore
                hxl_hxh = bytes([data[i + 2], data[i + 3]])  # type: ignore
                hyl_hyh = bytes([data[i + 4], data[i + 5]])  # type: ignore
                hzl_hzh = bytes([data[i + 6], data[i + 7]])  # type: ignore

                combined_x = int.from_bytes(hxl_hxh, byteorder="little", signed=True)
                combined_y = int.from_bytes(hyl_hyh, byteorder="little", signed=True)
                combined_z = int.from_bytes(hzl_hzh, byteorder="little", signed=True)

                magnetic_strength = math.sqrt(
                    combined_x**2 + combined_y**2 + combined_z**2
                )
                direction = math.atan2(combined_y, combined_x) * (180 / math.pi)
                if direction < 0:
                    direction += 360

        return direction, magnetic_strength
