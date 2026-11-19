# 세션 3 · 보안 테스트와 DevSecOps

GitHub Actions는 [워크플로](../.github/workflows/session-3.yml)를 읽어 [check.sh](check.sh)의 각 단계를 실행합니다. ZAP의 수동적 검사 설정(정상 요청과 응답을 관찰하는 검사)은 [GitHub 설정 폴더](../.github/zap-passive.yml)에 있습니다.

저장소 루트에서 기존 세션 2 테스트를 먼저 확인할 수 있습니다.

```bash
./session3/check.sh build
./session3/check.sh start
./session3/check.sh test
./session3/check.sh stop
```

스크립트는 기본적으로 `session3` Compose 프로젝트와 별도 포트(18000, 18001, 18501)를 사용합니다. `stop`은 이 프로젝트의 실습용 컨테이너와 볼륨을 삭제합니다.

GitHub에서는 강의 저장소를 Fork(내 계정으로 복사)하고, `session-3/`로 시작하는 브랜치에 변경을 올려 Actions 결과를 확인합니다. PR을 열어도 검사가 실행됩니다.

| 명령 | 확인 내용 |
|---|---|
| `source` | Bandit으로 Python 소스 검사. 세션 1의 개선 전 예제는 강의에서 비교할 항목입니다. |
| `dependencies` | pip-audit로 세션 1·2의 Python 의존성 검사 |
| `images` | Trivy로 빌드한 세션 2 이미지 검사 |
| `passive` | ZAP으로 세션 2 Gateway의 정상 응답 관찰 |
| `test` | 세션 2 인증·결제 검증과 Gateway 테스트 |

보안 스캔의 발견 사항은 보고서에서 확인합니다. 테스트 실패와 검사 도구 실행 오류는 워크플로 실패로 표시됩니다. ZAP 보고서는 GitHub Actions 실행 결과에서 내려받을 수 있습니다.
