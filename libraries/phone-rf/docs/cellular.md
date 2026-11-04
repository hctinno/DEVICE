# cellular 명령 카탈로그

정적 분석 결과입니다. static_ready는 문법 생성 가능, needs_profile은 인수 범위 지정 필요, reference_only/blocked는 실행 불가입니다. 실기기 검증 명령은 0개입니다.

| ID | 기능 | 명령 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| cellular_mitsrfts | MITSRFTS 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:238](../evidence/UserOpenCommand.java) |
| cellular_prxdrxck | PRXDRXCK 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:372](../evidence/UserOpenCommand.java) |
| cellular_rfbkoffc | RFBKOFFC 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:553](../evidence/UserOpenCommand.java) |
| cellular_rfbycode | RFBYCODE 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:557](../evidence/UserOpenCommand.java) |
| cellular_rfevtait | RFEVTAIT 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:369](../evidence/UserOpenCommand.java) |
| cellular_rfmipitt | RFMIPITT 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:604](../evidence/UserOpenCommand.java) |
| cellular_rfnvchks | RFNVCHKS 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:556](../evidence/UserOpenCommand.java) |
| cellular_rfsaronoff | RFSARONOFF 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:705](../evidence/UserOpenCommand.java) |
| cellular_secnrssi | SECNRSSI 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:554](../evidence/UserOpenCommand.java) |
| cellular_svcbandb | SVCBANDB 정책 등록만 확인 | `인수 미확인` | blocked | [UserOpenCommand.java:548](../evidence/UserOpenCommand.java) |

## 인수·전제조건·종료

### cellular_mitsrfts

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_prxdrxck

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfbkoffc

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfbycode

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfevtait

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfmipitt

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfnvchks

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_rfsaronoff

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_secnrssi

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.

### cellular_svcbandb

{}

종료 후보: 미확인 또는 해당 없음

LTE/NR RF 인수·허용 범위·TX 정지·응답 미확인. 다른 제조사 AT 명령을 대입하지 않습니다.
