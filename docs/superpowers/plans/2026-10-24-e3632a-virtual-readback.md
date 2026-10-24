# E3632A-VIRTUAL-READBACK-019 실행 계획

[고정 설계](../specs/2026-10-24-e3632a-virtual-readback-design.md)를 따른다. DELTA015/MAX/이전 branch·원문/실패 증거를 보존한다.

1. 기존 PowerSupply 공개 observation snapshot/measure와 두 E3632A 원문 프로필을 읽고 새 branch/신규3파일·가상 범위를 ACK한다. read action은 없으므로 추가하지 않는다. usage에 정확 DTO/오류와 예산·역사 cache를 먼저 동결한다.
2. 누락 모듈 RED 뒤 설정/enable/유효 측정을 분리하는 observation1/선택적 measure1 경계를 구현한다. snapshot과 실제 device 명령을 구분하며 부하/RF/전원 엔진과 vendor transport는 새로 만들지 않는다.
3. OFF0표식·보호/CC/실패/문맥/변조·교체 callback/부분진행·cache·bytes/depth·무I/O 및 관련 회귀를 검사한다. P01 기존 근거는 준비된 행부터 대조하고 unknown을 승격하지 않는다.
4. 실제 기존 Fleet 합성 실행/원본 전후 SHA·실패/원문 보존과 문서검사 후 소유3파일 commit/push/원격 SHA로 인계한다. 독립 지적 소유 수정→총괄 회귀/게시→다음 단위로 이어간다.
