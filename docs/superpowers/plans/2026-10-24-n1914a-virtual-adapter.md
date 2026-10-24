# N1914A 합성 전송 어댑터 실행 계획

2026-10-24 · Asia/Seoul. [고정 설계](../specs/2026-10-24-n1914a-virtual-adapter-design.md)를 개발3 신규3파일에서 실행한다.

1. 현재 SOURCE005 완료 브랜치/미커밋을 보존하고 총괄의 catalog 공통base에서 새 전용 개발 브랜치를 준비한다. 원문은 기존 N1914A command map/사용법을 재사용하고 P01 CTRL001 새 수집을 기다리지 않는다.
2. 최소 정확 모델·단위·tick·reply/오류·원래 정상 값 대조의 RED 검사를 작성한다. 고정 공개 DTO/에러 코드·canonical transcript digest를 사용법에 기록하고 순차 명령·오류 확인·bounded polling을 구현해 GREEN으로 만든다.
3. 실패 prefix·정리/취소·timeout·단절복구·동시/중복ID·caller/반환 alias·sensor not_assessed를 검사한다. 새 상태 엔진을 복제하지 않고 기존 VirtualLab만 실행한다.
4. 실제 VirtualLab 정상/단절복구/취소/timeout 합성 증거와 전용·VirtualLab/Session 회귀를 실행한다. 원래 source 및 공유 폴더 불변을 확인하고 자신의3파일만 커밋·푸시한다.
5. 총괄에 SHA·정확 DTO/코드·검증 수/경로·한계를 전달한다. 독립 리뷰 수정 후 root 통합·게시를 이어가고 SDK/실물 결과로 승격하지 않는다. 현재 새 사용자 준비물0.
