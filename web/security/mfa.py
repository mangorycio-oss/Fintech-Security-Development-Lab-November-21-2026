import secrets
import time

import pyotp


def new_secret():
    # 가입할 때 서버와 인증기가 공유할 무작위 Base32 설정 키를 만든다.
    return pyotp.random_base32()


def matching_step(secret, code, last_step):
    # 현재 시각을 TOTP 주기(기본 30초)로 나눠 시간 구간 번호를 구한다.
    totp = pyotp.TOTP(secret)
    step = int(time.time()) // totp.interval

    # 기기의 시계 차이나 입력 지연을 고려해 현재, 직전, 다음 구간을 확인한다.
    for candidate in (step, step - 1, step + 1):
        # 마지막 성공 구간보다 새로워야 하며, 코드는 타이밍 비교 공격을 줄이는 함수로 대조한다.
        if candidate > last_step and secrets.compare_digest(
            totp.at(candidate * totp.interval), code
        ):
            return candidate

    return None
