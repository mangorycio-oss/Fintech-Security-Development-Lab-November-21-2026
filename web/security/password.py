from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError

# Type.ID는 Argon2id 방식을 선택한다.
hasher = PasswordHasher(type=Type.ID)

# 존재하지 않는 사용자도 해시 검증을 수행해 로그인 응답 시간의 차이를 줄인다.
DUMMY_HASH = hasher.hash("unused-practice-password")


def hash_password(password):
    # 가입할 때마다 무작위 솔트를 생성한다. 반환 문자열에 솔트와 해시 설정도 들어 있다.
    return hasher.hash(password)


def verify_password(encoded, password):
    # 저장된 해시 문자열의 솔트와 설정으로 입력한 비밀번호가 일치하는지 검증한다.
    try:
        return hasher.verify(encoded, password)
    except VerifyMismatchError:
        # 비밀번호 불일치는 로그인 실패로 처리한다.
        return False
