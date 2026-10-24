# RsInstrument Simulation probe 구현 계획

2026-10-24 · Asia/Seoul. [고정 범위](../specs/2026-10-24-rsinstrument-simulation-probe-design.md)를 개발2 신규3파일에서 실행한다.

1. MODEL-PROBE005 최종 게시와 독립 리뷰 소유 수정을 우선한다. 새 전용 branch에서 실제 vendor Simulation의 parent/child·증거·실패 검사를 RED로 만든다.
2. P01 CTRL003의 고정 package·LICENSE·deps·Simulation source 영수증이 오면 총괄이 독립 인수·해시 대조 후 개발2에 전달한다. 원문/권리·정확 API를 읽고 private 환경만 준비한다. runtime 설치나 real device fallback은 없다.
3. 고정 Simulation 선택과 socket/DNS/VISA 금지를 함께 검증하고 캐시/완료·오류/미확인 명령 관측을 새 증거로 남긴다. 실제 SDK 실행 증거가 없으면 실제 통과로 표시하지 않는다.
4. 전용/기존 probe 회귀·정리/핀·증거 무결성을 확인하고 자기3파일만 커밋·푸시한다. 독립 리뷰 수정/총괄 통합·게시와 다음 backend 단위로 이어간다. 실물·RF물리·실제AI 미검증/사용자 새 준비0을 유지한다.
