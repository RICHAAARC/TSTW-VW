# 测试用例构建约束

## 一、文档定位

本文档是项目后续所有测试用例新增、修改、拆分、合并与迁移时必须遵守的长期约束契约。本文档不描述某一次具体测试整理任务，也不替代 `docs/test_list.md` 的清单作用；其职责是定义测试目录边界、命名规则、marker 策略、fixture 使用规则、外部资源约束、耗时分层、CI 默认口径与禁止事项。

本文档适用于以下目录和文件：

```text
tests/
pyproject.toml
docs/test_list.md
docs/field_registry.md
docs/naming_governance.md
docs/placeholder_random_governance.md
docs/file_organization.md
tools/harness/
paper_workflow/
experiments/
scripts/
```

后续任何测试新增或重构均必须满足：

```text
1. 一个测试文件只服务一种主要测试类型；
2. 测试目录必须反映验证对象和运行成本；
3. marker 必须反映执行代价、外部依赖与 CI 口径；
4. 约束测试默认执行，重型 runtime 默认排除；
5. 功能测试可拆为 quick 与 integration 两层；
6. smoke 是关键端到端路径，不等同于所有重型测试；
7. formal 只用于 formal gate 与正式完成条件；
8. 所有测试命名、fixture 命名、临时 artifact 字段必须遵守项目命名与 placeholder / random 治理。
```

---

## 二、测试目录总结构

项目测试目录固定为三层主结构：

```text
tests/
├── constraints/
│   ├── test_naming.py
│   ├── test_boundary.py
│   ├── test_placeholder_random.py
│   ├── test_protocol_artifact_schema.py
│   ├── test_notebook_contract.py
│   └── ...
├── functional/
│   ├── test_mp4_io.py
│   ├── test_vae_backend.py
│   ├── test_video_attacks.py
│   ├── test_quality_metrics.py
│   ├── test_temporal_metrics.py
│   ├── test_packager.py
│   └── ...
└── integration/
    ├── test_real_video_attack_matrix.py
    ├── test_real_video_vae_latent_probe.py
    ├── test_table_rebuild.py
    ├── test_formal_gate.py
    └── ...
```

该目录结构是测试设计的首要归属规则。新增测试时不得先创建根目录平铺测试文件，必须先判断其属于 `constraints/`、`functional/` 还是 `integration/`。

### （一）`tests/constraints/`

`constraints/` 保存约束测试。约束测试应满足：

```text
1. 主要验证命名、边界、schema、字段、文档、配置、审计、formal gate、Notebook contract、release boundary；
2. 原则上不执行真实 I/O；
3. 不实例化真实 VAE、真实 runner、真实 attack runtime；
4. 不读取真实数据集；
5. 不依赖 GPU、ffmpeg、LPIPS、diffusers 模型；
6. 默认必须执行；
7. 典型 marker 为 unit 和 constraint。
```

适合放入 `constraints/` 的测试包括：

```text
文件组织边界；
main/ 不依赖 paper_workflow/；
main/ 不包含 Colab / Drive 逻辑；
命名治理；
placeholder / random 字段治理；
protocol artifact schema；
field registry 完整性；
Notebook cell 顺序与导入边界；
formal 模式阻断 placeholder；
release boundary；
审计工具最小行为；
配置文件结构与必填字段。
```

### （二）`tests/functional/`

`functional/` 保存功能测试。功能测试应满足：

```text
1. 验证某个具体函数、模块或 backend 的可运行行为；
2. 可以有轻量 I/O；
3. 可以写临时 mp4、npy、json、csv；
4. 可以使用 mock backend、tiny video fixture、fake model；
5. 默认仅执行 quick 部分；
6. 真实 ffmpeg、真实 mp4、真实 frame metric 可标记 quick 或 integration，取决于耗时和资源；
7. 不应运行完整 runner 或 formal gate。
```

适合放入 `functional/` 的测试包括：

```text
mp4 read / write / metadata probe；
frame standardization；
VAE registry；
mock AutoencoderKL encode / decode；
real video attack 单个模块；
quality metrics frame-level calculation；
temporal metrics frame-level calculation；
tar.zst packager 单模块；
table builder 单函数；
method embedding / detection 纯函数行为；
tubelet partition；
sync alignment；
fusion rule。
```

### （三）`tests/integration/`

`integration/` 保存集成测试。集成测试应满足：

```text
1. 运行多个模块构成的真实或近真实流程；
2. 可以实例化 runner；
3. 可以生成 run_root；
4. 可以调用 ffmpeg；
5. 可以使用真实 mp4 fixture；
6. 可以执行 records / thresholds / tables / reports 闭环；
7. 默认不执行；
8. 必须显式 marker 为 integration、smoke、slow 或 formal 中至少一个。
```

适合放入 `integration/` 的测试包括：

```text
real_video_vae_latent tiny run；
attack matrix 全量实例化；
records → tables → report rebuild；
formal checker PASS / FAIL 条件；
notebook handoff artifact 检查；
packaged run archive 检查；
阶段性 probe runner；
paper_main 或 paper_mechanism 子流程 smoke。
```

---

## 三、marker 策略

`pyproject.toml` 中的 pytest marker 必须统一为以下集合：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = ["-m", "(constraint or unit or quick) and not integration and not smoke and not slow and not formal"]
markers = [
    "unit: 极快，无 I/O，无外部依赖，适用于纯函数、静态约束和轻量 schema 测试",
    "constraint: 约束测试；等价于 unit 的治理别名，用于命名、边界、schema、文档和 formal gate 约束",
    "quick: 短时间可完成的轻量功能测试，可包含临时文件、mock backend、小型 mp4 fixture",
    "integration: 需要真实 I/O、runner 实例化、跨模块 artifact 或较重依赖的集成测试，默认排除",
    "smoke: 关键端到端路径，默认排除，但 CI 主流水线应定期运行",
    "slow: 单个测试或测试文件典型耗时超过 30 秒，默认排除",
    "formal: formal gate 或正式完成条件专用测试，默认排除"
]
```

若项目希望默认执行更保守，可使用：

```toml
addopts = ["-m", "unit or constraint"]
```

但不允许继续使用单一的：

```text
not slow and not formal and not smoke
```

原因是该口径会错误纳入未标记但实际偏重的功能测试，导致默认测试集混入 mp4 I/O、packager tiny run、backend build 等 runtime 成本。

### （一）`unit`

`unit` 表示极快测试。必须满足：

```text
无真实 I/O；
无外部命令；
无模型加载；
无 runner；
无真实视频写入；
单个测试通常小于 0.1 秒；
可在任意 CPU 环境稳定运行。
```

示例：

```python
@pytest.mark.unit
def test_tubelet_partition_digest_is_stable():
    ...
```

### （二）`constraint`

`constraint` 是治理约束测试别名。约束测试原则上也应是 `unit`。建议同时标记：

```python
@pytest.mark.unit
@pytest.mark.constraint
def test_main_does_not_import_paper_workflow():
    ...
```

仅当约束测试需要读取文件树或解析 notebook JSON 时，可以只标记：

```python
@pytest.mark.constraint
```

但仍必须默认执行。

### （三）`quick`

`quick` 表示轻量功能测试。允许：

```text
写入 tmp_path；
生成极小 mp4；
调用 mock VAE；
调用轻量 ffmpeg 命令；
构造 fake records；
运行单模块 packager；
运行单模块 metric。
```

不允许：

```text
完整 runner；
真实大数据集；
真实模型下载；
GPU 必需路径；
超过 30 秒；
formal gate 完整闭环。
```

### （四）`integration`

`integration` 表示跨模块集成测试。只要满足以下任一条件，就必须标记为 `integration`：

```text
实例化 runner；
生成 run_root；
读取或写入多个 artifact 子目录；
重建 tables / reports；
调用 attack matrix；
调用 VAE backend + attack + metric 的组合；
依赖 processed dataset manifest；
需要 session 级 fixture 缓存。
```

### （五）`smoke`

`smoke` 是关键端到端路径。必须同时标记 `integration`：

```python
@pytest.mark.integration
@pytest.mark.smoke
def test_real_video_vae_latent_tiny_run_smoke(...):
    ...
```

`smoke` 不表示“轻量”，而表示“关键路径”。其默认排除，但 CI 可以定期运行：

```bash
python -m pytest -m smoke
```

### （六）`slow`

满足以下任一条件必须标记为 `slow`：

```text
单个测试典型耗时超过 30 秒；
需要下载或复制大量数据；
需要处理多个视频；
运行完整 attack matrix；
运行 proof profile；
重复生成多个 run root；
模型加载耗时不可忽略。
```

### （七）`formal`

`formal` 只用于 formal gate、正式完成条件与发布前检查。必须同时标记 `integration`，必要时同时标记 `slow`：

```python
@pytest.mark.integration
@pytest.mark.formal
def test_real_video_vae_latent_formal_pass_requires_real_runtime(...):
    ...
```

`formal` 测试不应用于普通功能行为。普通功能行为应拆到 `functional/`。

---

## 四、测试文件命名约束

### （一）全局命名规则

所有测试文件必须使用 `snake_case`，并且禁止弱阶段编号、弱版本后缀和无机制语义名称。

禁止：

```text
test_stage2_*.py  # 禁止：弱阶段编号
test_stage_2_*.py  # 禁止：弱阶段编号
test_v1_*.py  # 禁止：弱版本后缀
test_p2_*.py  # 禁止：弱版本后缀
test_new.py
test_final.py
test_best.py
test_temp.py
test_fix.py
```

允许：

```text
test_real_video_vae_latent_constraints.py
test_real_video_vae_latent_functional.py
test_real_video_vae_latent_integration.py
test_tubelet_partition.py
test_temporal_synchronization.py
test_protocol_artifact_schema.py
test_notebook_contract.py
```

注意：历史阶段说明只允许位于 `docs/builds/**`。测试文件名禁止使用 `stage0`、`stage1`、`stage2` 等形式。

### （二）按测试类型命名

如果一个主题同时存在约束测试、功能测试和集成测试，应拆成多个文件：

```text
tests/constraints/test_real_video_vae_latent_contract.py
tests/functional/test_real_video_vae_latent_backend.py
tests/integration/test_real_video_vae_latent_probe.py
```

不要写成：

```text
tests/test_real_video_vae_latent.py
```

因为该文件极易混合 schema、backend、runner、packager 和 formal gate。

### （三）测试函数命名

测试函数应表达被验证的事实，不应表达实现细节或修复历史。

推荐：

```python
def test_formal_runtime_rejects_placeholder_vae_backend():
    ...

def test_video_attack_registry_uses_real_video_runtime_for_formal_profile():
    ...

def test_records_to_tables_rebuild_preserves_threshold_identity():
    ...
```

禁止：

```python
def test_fix_bug():
    ...

def test_stage2_patch():  # 禁止：弱阶段编号
    ...

def test_new_runner():
    ...

def test_final_pass():
    ...
```

---

## 五、测试文件拆分与合并规则

### （一）拆分规则

同一个测试文件中如果同时包含以下内容，必须拆分：

```text
约束测试 + 功能测试；
功能测试 + runner 集成测试；
quick 测试 + slow 测试；
普通功能测试 + formal gate 测试；
mock backend 测试 + 真实模型加载测试；
单模块 metric 测试 + 完整 run_root rebuild 测试。
```

拆分命名示例：

```text
test_real_video_attack_registry_constraints.py
  只保留 registry mode、禁止 placeholder、配置字段约束。

test_real_video_attack_registry_functional.py
  只保留单个 attack 对 tiny mp4 的功能行为。

test_real_video_attack_matrix_integration.py
  只保留完整 attack matrix 的 runner-level 集成路径。
```

### （二）合并规则

多个测试文件如果满足以下条件，应合并：

```text
同属 constraints；
测试对象同质；
每个文件只有 1–2 个小测试；
无外部 I/O；
无 runner；
合并后文件职责仍单一。
```

合并示例：

```text
tests/test_semantic_naming_governance.py
tests/test_naming_conventions.py
→ tests/constraints/test_naming.py
```

```text
tests/test_core_boundary_layering.py
tests/test_stage_boundaries.py
tests/test_repository_intake.py
→ tests/constraints/test_boundary.py
```

不应合并：

```text
mp4 IO 测试 + VAE backend 测试；
packager 测试 + runner smoke 测试；
formal gate 测试 + naming test；
quality metric 测试 + temporal metric 测试。
```

### （三）一个文件只服务一种主要测试类型

每个测试文件必须在文件头部注明：

```python
"""Constraint tests for repository naming governance."""
```

或：

```python
"""Quick functional tests for real video MP4 IO."""
```

或：

```python
"""Integration smoke tests for real video VAE latent probe."""
```

文件头说明必须与所在目录和 marker 一致。

---

## 六、fixture 与资源使用约束

### （一）fixture 分层

测试 fixture 必须按资源成本分层：

```text
tests/fixtures/static/
  用于纯约束测试的 JSON、YAML、Markdown、schema 小样本。

tests/fixtures/tiny_video/
  极小 mp4、frame tensor、视频 metadata，用于 quick functional。

tests/fixtures/mock_model/
  mock VAE、mock LPIPS、fake backend，用于 quick functional。

tests/fixtures/run_roots/
  仅保存极小 synthetic run root 样例，不保存真实大结果。
```

### （二）session 级 fixture 缓存

凡是满足以下任一条件，必须使用 session 级 fixture 缓存：

```text
生成 tiny mp4；
调用 ffmpeg；
构造 tiny run_root；
构造 processed dataset fixture；
构造 fake VAE model directory；
构造 attack matrix runtime objects；
构造 records / thresholds / tables / reports 闭环。
```

推荐写法：

```python
@pytest.fixture(scope="session")
def tiny_mp4_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("tiny_mp4_fixture")
    ...
    return video_path
```

禁止在多个测试函数中重复生成相同资源。

### （三）禁止真实外部资源默认进入测试

默认测试不得依赖：

```text
真实 Google Drive；
真实 Colab；
真实 DAVIS / UCF101 / MSR-VTT 原始数据；
真实 Hugging Face 下载；
真实 VAE 权重；
真实 LPIPS 权重；
GPU；
网络访问。
```

若必须测试这些路径，只能放入 `integration/`，并标记：

```python
@pytest.mark.integration
@pytest.mark.formal
@pytest.mark.slow
```

且必须通过环境变量显式启用，例如：

```text
TSTW_ENABLE_REAL_MODEL_TESTS=1
TSTW_ENABLE_REAL_DATASET_TESTS=1
TSTW_ENABLE_COLAB_CONTRACT_TESTS=1
```

---

## 七、I/O 与 artifact 约束

### （一）测试输出位置

测试只能写入 pytest 提供的临时目录：

```text
tmp_path
tmp_path_factory
```

禁止写入：

```text
outputs/
artifacts/
records/
thresholds/
tables/
figures/
reports/
/content/
/content/drive/
用户真实 Google Drive 路径
仓库根目录临时文件
```

例外：测试专门验证 path policy 或 output layout 时，可以构造临时 run root，但必须位于 `tmp_path` 下。

### （二）run_root fixture

任何生成 run_root 的测试必须使用：

```python
run_root = tmp_path / "run_root"
```

或 session fixture：

```python
@pytest.fixture(scope="session")
def tiny_run_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("tiny_run_root")
    ...
    return root
```

run_root 中必须遵守项目输出布局：

```text
records/
thresholds/
artifacts/
tables/
figures/
reports/
failure_case_gallery/
logs/
```

### （三）artifact digest

任何测试生成的正式 artifact-like 文件，如果用于断言 records / manifest / table 重建，必须检查 digest 或 metadata。禁止只检查文件存在。

推荐断言：

```python
assert artifact_path.exists()
assert artifact_path.stat().st_size > 0
assert payload["artifact_digest"].startswith("sha256:") or len(payload["artifact_digest"]) == 64
```

---

## 八、Notebook 与 workflow 测试约束

Notebook 测试属于约束测试，默认应放在：

```text
tests/constraints/test_notebook_contract.py
```

Notebook 测试只允许检查：

```text
notebook 文件名；
cell 标题；
禁止直接写 records / thresholds / tables；
是否调用 experiments runner；
是否调用 scripts checker / packager；
是否使用 FAMILY_ID；
是否遵守 raw / processed / session model / family result 边界；
是否不 import main.colab.*。
```

Notebook 测试不得执行 notebook。执行 notebook 属于 workflow integration 或人工 Colab 验证，不属于默认 pytest。

Notebook 名称必须遵守：

```text
paper_workflow/build_processed_real_video_dataset.ipynb
paper_workflow/run_real_video_vae_latent_probe.ipynb
```

不允许新增：

```text
Stage2_*.ipynb  # 禁止：弱阶段编号
*_Colab.ipynb
Run_*.ipynb
notebook_v1.ipynb  # 禁止：弱版本后缀
```

---

## 九、配置、字段与 schema 测试约束

配置测试属于 `constraints/`。它们应验证：

```text
配置文件存在；
配置 key 使用 snake_case；
没有弱阶段命名；
没有未登记 placeholder / random 字段；
正式 config 不引用 placeholder backend；
formal config 不使用 mock 模型；
threshold protocol 不允许 test leakage；
attack-specific threshold 被禁止；
method_variant 使用机制语义。
```

字段测试必须与 `docs/field_registry.md` 保持一致。任何测试引入新的 record key、manifest key、fixture key，都必须同时考虑：

```text
是否属于 governed field；
是否需要登记到 field_registry；
是否有 placeholder / random suffix；
是否 allowed_in_claims=false；
是否 replacement_required=true。
```

禁止在测试 fixture 中随意创造未登记字段，然后让 schema 容忍它。

---

## 十、release boundary 测试约束

release boundary 测试属于 `constraints/`，应默认执行。必须覆盖：

```text
main/ 不依赖 paper_workflow/；
main/ 不依赖 Google Drive 绝对路径；
main/ 不依赖 Colab API；
main/ 不包含 stage-specific runner；
main/ 不包含 placeholder / random core 文件；
paper_workflow/ 不作为 release 默认入口；
experiments/ 可以依赖 main/，main/ 不依赖 experiments/；
scripts/ 可以依赖 main/，main/ 不依赖 scripts/；
docs/builds/ 不作为 release asset。
```

任何 release boundary 测试不得执行真实 runner。它应通过 AST、文本扫描、路径扫描或 import graph 方式完成。

---

## 十一、formal gate 测试约束

formal gate 测试属于 `integration/` 或 `constraints/`，根据是否运行 runtime 区分：

```text
只检查 checker 规则、manifest 字段、placeholder 阻断逻辑 → constraints + formal；
运行 tiny run_root 并检查 formal pass / fail → integration + formal；
运行真实模型或真实数据 → integration + formal + slow。
```

formal gate 测试不得为了通过而放松规则。必须阻断：

```text
placeholder VAE；
mock VAE formal；
tensor_npy video artifact formal；
placeholder_tensor_video_metrics formal；
未报告 attacked_negative_FPR；
test split 参与 threshold；
S_traj 非 null 于 real_video_vae_latent_probe；
Flow Matching / DiT dependency 提前进入；
notebook 直接写正式 outputs。
```

---

## 十二、耗时预算

测试文件必须满足以下典型耗时预算：

| 类型 | 单测试典型耗时 | 文件典型耗时 | 默认执行 |
|---|---:|---:|---:|
| `unit` | <0.1 s | <1 s | 是 |
| `constraint` | <0.5 s | <3 s | 是 |
| `quick` | <2 s | <10 s | 是，可按 CI 调整 |
| `integration` | 2–30 s | <60 s | 否 |
| `smoke` | 5–120 s | 可较重 | 否，CI 定期运行 |
| `slow` | >30 s | 不限 | 否 |
| `formal` | 不限 | 不限 | 否，仅专门流水线 |

如果某个测试超过其 marker 对应预算，必须调整 marker 或拆分测试。

---

## 十三、CI 推荐命令

### （一）默认开发检查

```bash
python -m pytest -m "(constraint or unit or quick) and not integration and not smoke and not slow and not formal"
```

### （二）只跑约束测试

```bash
python -m pytest tests/constraints -m "unit or constraint"
```

### （三）轻量功能测试

```bash
python -m pytest tests/functional -m quick
```

### （四）集成但非慢速

```bash
python -m pytest tests/integration -m "integration and not slow and not formal"
```

### （五）smoke 流水线

```bash
python -m pytest -m smoke
```

### （六）formal gate 流水线

```bash
python -m pytest -m formal
```

### （七）全量本地排查

```bash
python -m pytest
```

全量测试不作为默认开发命令。

---

## 十四、`docs/test_list.md` 维护规则

每次新增、删除、迁移或重命名测试文件后，必须更新：

```text
docs/test_list.md
```

该文档至少记录：

```text
测试文件路径；
节点数；
所属目录层；
主要 marker；
默认是否执行；
测试内容摘要；
是否依赖 I/O；
是否依赖外部命令；
是否需要真实模型或真实数据；
是否属于 release boundary / notebook contract / formal gate。
```

`docs/test_list.md` 不应由人工随意估计。推荐新增脚本：

```text
scripts/check_results/update_test_list.py
```

或：

```text
tools/harness/update_test_list.py
```

用于从 `pytest --collect-only` 和 marker 信息生成基础清单，再由人工补充说明。

---

## 十五、Codex 新增测试 Prompt 模板

后续让 Codex 新增测试时，必须使用以下约束模板：

```text
你必须遵守 docs/test_case_constraints.md。新增测试前先判断测试类型：constraints、functional 或 integration。禁止在 tests/ 根目录新增平铺测试文件。禁止使用 stage0、stage1、stage2、*_v1、*_p2 等弱命名。不得把约束测试和功能测试写在同一个文件。不得默认执行真实模型、真实数据、真实 runner 或 formal gate。

如果测试只验证命名、边界、schema、配置、formal 阻断或 Notebook contract，请放入 tests/constraints/，并标记 unit / constraint。

如果测试验证单个模块的行为，例如 mp4 IO、VAE registry、video attack、quality metric、packager，请放入 tests/functional/，并根据耗时标记 quick 或 integration。

如果测试运行 runner、生成 run_root、重建 tables / reports、执行 full attack matrix 或 formal checker，请放入 tests/integration/，并标记 integration；若是关键端到端路径，额外标记 smoke；若是 formal 完成条件，额外标记 formal；若超过 30 秒，额外标记 slow。

所有重型资源必须使用 session 级 fixture 缓存。所有测试输出必须写入 tmp_path 或 tmp_path_factory。禁止写入真实 outputs/、/content/drive/、Google Drive 或仓库根目录临时文件。

新增或迁移测试后，必须更新 docs/test_list.md，并运行对应 marker 口径的 pytest 命令。
```

---

## 十六、迁移旧测试的执行顺序

当前仓库若从平铺 `tests/` 迁移到分层结构，应按以下顺序执行：

```text
P0：更新 pyproject marker 集合，不移动文件；
P1：新增 tests/constraints、tests/functional、tests/integration 目录；
P2：迁移纯约束测试到 tests/constraints/；
P3：拆分混合文件，例如 ffmpeg compression、packager、records schema；
P4：迁移轻量功能测试到 tests/functional/；
P5：迁移 runner、rebuild、formal、smoke 到 tests/integration/；
P6：引入 session 级 fixture 缓存，消除重复 tiny run；
P7：更新 docs/test_list.md 与 audit；
P8：删除旧根目录平铺测试文件。
```

在 P8 之前允许保留兼容导入或空 wrapper，但 wrapper 不得长期存在。

---

## 十七、最终完成标准

测试体系整理完成后，必须满足：

```text
1. tests/ 根目录下不再平铺大量 test_*.py；
2. 所有测试文件位于 constraints、functional 或 integration；
3. 所有测试文件名为 snake_case；
4. 无 test_stage2_*、test_v1_*、test_p2_* 等弱命名；
5. 约束测试默认执行且无重型 I/O；
6. functional 测试中 quick 与 integration 已区分；
7. integration、smoke、formal、slow 默认排除；
8. notebook contract 测试不执行 notebook；允许直接读取 raw notebook JSON，并可基于 markdown cell 的 `metadata.step_key` 验证 governed step 顺序；不得强制要求标题文本暴露 step key slug；
9. formal gate 测试不放松阻断规则；
10. runner-backed 测试统一放入 integration；
11. 重型 fixture 使用 session 级缓存；
12. 测试输出只写 tmp_path；
13. docs/test_list.md 与实际 pytest collect 结果一致；
14. pyproject.toml marker 定义完整；
15. 默认 pytest 命令不再隐式运行 mp4 / runner / packager 重型路径。
```
