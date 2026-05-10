# Harness Engineering

鏈洰褰曞畾涔?`protocol_skeleton` 闃舵鐨勫彲鎵ц宸ョ▼闂ㄧ銆?
## Scope

- `tools/harness/lib/` 鎻愪緵鏍囧噯搴撳疄鐜扮殑鎵弿銆佸懡鍚嶈鍒欍€佸瓧娈佃鍒欎笌 JSON 鎶ュ憡鑳藉姏銆?- `tools/harness/audits/` 鎻愪緵鍛藉悕銆佸瓧娈点€侀樁娈靛绾︺€侀樁娈?0 support config銆侀槇鍊煎崗璁€乶otebook bypass 涓?skill 瀛樺湪鎬у璁°€?- `configs/schema/protocol_artifact_schema.json` 鍐荤粨闃舵 0 鐨?records銆乼hresholds銆乵anifest 涓?table layout schema skeleton銆?- `configs/attacks/identity_attack_placeholder.json` 涓?`configs/ablation/ablation_placeholder.json` 鍐荤粨闃舵 0 鐨?attack 涓?ablation support config skeleton銆?- `tools/harness/run_all_audits.py` 缁熶竴姹囨€诲璁★紝骞跺皢鎽樿鍐欏叆 `audit_reports/harness_audit_summary.json`銆?- `tests/` 鎻愪緵 pytest 鏈€灏忛棴鐜紝楠岃瘉鍛藉悕銆佸瓧娈垫不鐞嗐€佸崗璁绾︿笌姹囨€诲璁°€?
## Layer Boundary

- `tools/harness/` 鏄灞?governance 灞傦紝涓嶅睘浜?`method_core`銆乣protocol_core` 鎴栨湭鏉?`minimal_demo` 鐨勮繍琛屾椂渚濊禆銆?- `main/` 鍙互琚?harness 鍜?tests 妫€鏌ワ紝浣?`main/` 涓嶅緱鍙嶅悜 import `tools/harness` 鎴?`tests`銆?- protocol runtime validation 鍙互淇濈暀鍦?`main/core/`銆乣main/protocol/` 涓?`main/analysis/`锛屼絾 naming governance銆乻tage progression guard銆乻kill audit 鍙兘鐣欏湪澶栧眰娌荤悊灞傘€?
## Runtime Guarantees

- Harness 鑴氭湰浠呬緷璧?Python 鏍囧噯搴撱€?- `audit_reports/` 浠呬綔涓鸿繍琛屾椂瀹¤杈撳嚭鐩綍锛屼笉灞炰簬姝ｅ紡璁烘枃 `outputs/`銆?- 褰撳墠闃舵瀹炵幇 placeholder / random 椹卞姩鐨?records writer銆乼hreshold calibrator銆乼able builder銆乸rotocol runner 涓?ablation runner scaffold銆?- 褰撳墠闃舵浠呭喕缁撳苟鎵ц protocol skeleton runtime protocol skeleton锛屼笉钀藉湴鐪熷疄绠楁硶鎴栫湡瀹炴ā鍨嬩骇鐗┿€?- 褰撳墠闃舵浠呭喕缁?support config銆乧laim 杈圭晫涓?release boundary锛屼笉鍒涘缓鐪熷疄 `minimal_release/` 鎴?notebook-only runtime銆?
## Required Entry Commands

```bash
pytest -q
python tools/harness/run_all_audits.py
```
