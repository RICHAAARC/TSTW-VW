# VAE batching 修改说明

## 一、文档定位

本文档用于指导 Codex 在当前真实项目代码中实现 cross-event VAE batching。目标是把阶段 2 runner 中当前“一条 event 一次 VAE decode / re-encode”的执行方式，改为“多条同构 event 合并后一起进入 VAE”，以降低 Stage2 机制选参与重复运行成本。

本次变更必须严格限定为运行加速层，不改变阶段 2 方法语义、records 语义、threshold 语义、mechanism decision 语义或 formal checker 判定语义。

当前真实代码状态如下：

```text
VAE backend：main/vae/diffusers_autoencoder_kl_framewise.py
阶段 2 runner：experiments/real_video_vae_latent_probe/runner.py
notebook workflow helper：paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
notebook：paper_workflow/run_real_video_vae_latent_probe.ipynb
execution preset 目录：configs/runtime_profiles/*.json
backend config：configs/backend/real_video_vae_latent.json
```

其中需要明确两点：

```text
configs/runtime_profiles/*.json 当前是 notebook / runtime 预设层，不是 runner 直接解析的 cross-event batching 配置优先级来源；
configs/backend/real_video_vae_latent.json 是 VAE backend 配置，不应作为 cross-event batching 的默认来源。
```

当前 `diffusers_autoencoder_kl_framewise.py` 已经支持**单个视频内部**的 frame batch：

```text
encode_video(video_batch: [F,H,W,3])
→ 内部按 batch_size_frames 分块 encode

decode_video(latent_batch: [F,C,H_lat,W_lat])
→ 内部按 batch_size_frames 分块 decode
```

但当前 `runner.py` 仍按 event 单条调用：

```text
_event_1 latent → decode_video → write decoded mp4 → attack → encode_video → detect → record
_event_2 latent → decode_video → write decoded mp4 → attack → encode_video → detect → record
...
```

本次目标是新增 opt-in 调度：

```text
多条 decode request → concat latent frames → decode_video 一次或少数几次 → split → 写每个 event 的 decoded mp4
多条 re-encode request → concat attacked frames → encode_video 一次或少数几次 → split → 写每个 event 的 reencoded latent
```

注意：本次只批量 VAE decode / VAE encode，不批量 video attack、不批量 detection、不批量 record writing、不批量 threshold calibration。

---

## 二、强制边界

### （一）允许修改

允许新增或修改：

```text
experiments/real_video_vae_latent_probe/runner.py
experiments/real_video_vae_latent_probe/vae_batching.py
paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
paper_workflow/run_real_video_vae_latent_probe.ipynb
tests/functional/test_cross_event_vae_batching_config.py
tests/integration/test_cross_event_vae_batching_equivalence.py
tests/integration/test_cross_event_vae_batching_artifact_contract.py
tests/integration/test_cross_event_vae_batching_fallback.py
tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py
docs/gpu_runtime_optimization_governance.md
docs/field_registry.md
```

如 notebook 预设层确实需要展示 batching 推荐值，可以同步更新 `configs/runtime_profiles/*.json`，但该更新只作为 notebook 侧 materialization 参考，不能把 runtime profile JSON 变成 runner 的额外配置优先级来源。

### （二）禁止修改

禁止修改以下语义：

```text
main/methods/temporal_tubelet_watermark/* 的算法逻辑；
main/protocol/calibrator.py 的 threshold 语义；
main/protocol/evaluator.py 的 TPR / FPR 语义；
experiments/real_video_vae_latent_probe/mechanism_audit.py 的 mechanism gate 语义；
scripts/check_results/check_stage2_mechanism_effect.py 的 mechanism decision 语义；
scripts/check_results/check_real_video_vae_latent_outputs.py 的 formal checker 放行条件；
records/event_scores.jsonl 中 evidence_scores 的定义；
S_tubelet、S_sync、S_final 的计算公式；
target_fpr、calibration split、test split 语义。
```

### （三）默认关闭

新增 cross-event VAE batching 后，默认必须关闭：

```json
{
  "cross_event_vae_batching_enabled": false
}
```

只有 runtime_config.json 或 CLI 显式开启时，才允许启用 batching。notebook 若需要 profile-scoped 默认值，应先把值 materialize 到 runtime_config.json。这样 sequential runner 继续作为 golden reference。

---

## 三、核心设计原则

### （一）只改变 VAE 调度，不改变 event 语义

batching 只能改变以下两个环节：

```text
latent tensor → VAE decode → video frames
video frames → VAE encode → latent tensor
```

以下环节必须保持 per-event：

```text
source sample build；
method.embed；
video attack materialization；
detection；
quality / temporal metrics；
record construction；
artifact manifest；
threshold calibration；
table rebuild；
mechanism audit。
```

### （二）只 batch 同构 request

同一 batch 中所有 request 必须满足：

```text
same operation: decode 或 encode；
same vae_backend_name；
same vae_backend_version；
same runtime_impl；
same device；
same dtype；
same latent shape；
same video frame shape；
same target_resolution；
same fps；
same runtime_profile；
same VAE scaling policy。
```

第一版不得为了凑 batch 做 padding、resize 或 shape 对齐。宁可 batch 小，也不能引入 shape 变换。

### （三）batching 必须可回退

如果 batch decode / encode 出现 CUDA OOM 或 runtime error，应按如下规则回退：

```text
batch_size = 8 → 4 → 2 → 1
```

当 batch_size 回到 1 时，行为应退化为 sequential-equivalent。必须在 mechanism_trace 或 runtime diagnostics 中记录：

```text
cross_event_vae_batching_enabled
cross_event_vae_batching_effective_decode_batch_size
cross_event_vae_batching_effective_encode_batch_size
cross_event_vae_batching_fallback_count
cross_event_vae_batching_fallback_reason
```

### （四）worker_count 与 batching 的关系

当前 runner 支持 `worker_count`，通过 `ThreadPoolExecutor` 把 event groups 分给多个 worker。VAE batching 与多线程 worker 同时打开会导致：

```text
多个线程共享同一个 VAE 模型；
GPU 调度不可控；
batching 被 worker 分裂；
等价性测试复杂化。
```

因此第一版必须规定：

```text
cross_event_vae_batching_enabled = true 时，worker_count 必须为 1。
```

如果用户同时设置 `worker_count > 1`，runner 应 fail-fast，错误信息为：

```text
cross-event VAE batching requires worker_count == 1 in the first governed implementation
```

后续如果要支持 batching + worker，应另开独立任务。

### （五）第一版实现范围

第一版必须把范围限制在 real mp4 runtime：

```text
当 runner 走 mp4 video runtime 时，允许启用 cross-event batching；
当 imageio_ffmpeg 不可用或运行路径退化为 tensor_scaffold 时，不得在本补丁中宣称已支持 cross-event batching 等价性。
```

因此第一版只能二选一：

```text
方案 A：在 `_video_mp4_runtime_available() == false` 时 fail-fast 并提示 batching 仅支持 mp4 runtime；
方案 B：检测到 tensor_scaffold runtime 后整次 run 回退到 sequential 路径。
```

两种方案都可以，但必须固定其一并写入测试；不得对部分 event 静默混用 batched 与未声明的 tensor_scaffold batching 语义。

---

## 四、新增配置字段

### （一）runtime config 字段

新增以下 runtime config 字段：

```json
{
  "cross_event_vae_batching_enabled": false,
  "cross_event_vae_decode_batch_size": 4,
  "cross_event_vae_encode_batch_size": 4,
  "cross_event_vae_batch_grouping": "same_shape_same_backend",
  "cross_event_vae_batch_fallback_on_oom": true,
  "cross_event_vae_batch_write_trace": true
}
```

字段语义：

```text
cross_event_vae_batching_enabled：是否启用跨事件 VAE batching；
cross_event_vae_decode_batch_size：每个 decode batch 中最多包含多少个 event request；
cross_event_vae_encode_batch_size：每个 encode batch 中最多包含多少个 event request；
cross_event_vae_batch_grouping：当前只允许 same_shape_same_backend；
cross_event_vae_batch_fallback_on_oom：OOM 时是否自动降级；
cross_event_vae_batch_write_trace：是否写出 batching trace。
```

这些字段属于 runner 调度层配置：

```text
它们应来自 runtime_config.json 或 CLI；
它们不是 backend config 默认值；
它们也不应要求 runner 直接解析 configs/runtime_profiles/*.json。
```

### （二）notebook 预设 materialization

当前 runner 的真实分层是：

```text
先解析 runtime_profile 选择 protocol / coverage；
再加载 runtime_config.json 覆盖；
再解析 backend config 构建 VAE backend。
```

因此本设计要求：

```text
如果 notebook 想按不同 execution preset 提供 batching 推荐值，应先把这些值写入 runtime_config.json；
configs/runtime_profiles/*.json 可以作为 notebook 侧推荐值来源，但不能形成新的 runner precedence layer；
configs/backend/real_video_vae_latent.json 不提供 cross-event batching 默认值。
```

推荐的 notebook-side 默认 materialization 仍然可以是：

```json
{
  "cross_event_vae_batching_enabled": false,
  "cross_event_vae_decode_batch_size": 4,
  "cross_event_vae_encode_batch_size": 4,
  "cross_event_vae_batch_fallback_on_oom": true
}
```

### （三）CLI 参数

在 `experiments/real_video_vae_latent_probe/runner.py` 的 `main()` 中新增：

```text
--cross-event-vae-batching-enabled <true|false>
--cross-event-vae-decode-batch-size
--cross-event-vae-encode-batch-size
--cross-event-vae-batch-fallback-on-oom
```

CLI 优先级：

```text
CLI 显式参数 > runtime_config.json。
```

补充约束：

```text
runtime_profile 可以影响 notebook 侧推荐值，但不直接参与 runner 的 batching 配置优先级；
backend config 不参与 cross-event batching 配置优先级。
如果需要让 CLI 真正覆盖 runtime_config 中的 batching enable 开关，`--cross-event-vae-batching-enabled` 必须支持显式 true/false，而不是只支持单向 store_true。
```

注意：`--batch-size-frames` 继续表示 VAE backend 内部的 frame batch size；新增的 cross-event batch size 表示每个 batch 包含多少条 event request。两者不是同一概念，必须在文档和 notebook 中区分：

```text
batch_size_frames：单次 VAE 调用内部最多处理多少帧；
cross_event_vae_decode_batch_size：一次 batch decode 聚合多少条 event；
cross_event_vae_encode_batch_size：一次 batch encode 聚合多少条 event。
```

---

## 五、新增模块 `experiments/real_video_vae_latent_probe/vae_batching.py`

### （一）文件定位

新增：

```text
experiments/real_video_vae_latent_probe/vae_batching.py
```

该文件属于阶段 2 runner acceleration layer，不属于 `main/` 核心方法包。

### （二）必须提供的数据结构

建议使用 dataclass：

```python
@dataclass(frozen=True)
class CrossEventVaeBatchingConfig:
    enabled: bool
    decode_batch_size: int
    encode_batch_size: int
    grouping: str
    fallback_on_oom: bool
    write_trace: bool
```

```python
@dataclass(frozen=True)
class DecodeRequest:
    request_id: str
    cache_key: tuple[str, str, str]
    sample: Any
    latent_tensor: np.ndarray
    output_relpath: Path
    fps: int
    target_resolution: tuple[int, int]
    method_variant: str
    split: str
    event_id: str
```

```python
@dataclass(frozen=True)
class DecodeResult:
    request_id: str
    cache_key: tuple[str, str, str]
    video_frames: np.ndarray
    output_relpath: Path
    fps: int
    target_resolution: tuple[int, int]
    batch_group_id: str
    batch_request_count: int
    effective_batch_size: int
    fallback_count: int
    fallback_reason: str | None
```

```python
@dataclass(frozen=True)
class EncodeRequest:
    request_id: str
    cache_key: tuple[str, str]
    reference_sample: LatentSample
    video_frames: np.ndarray
    output_relpath: Path
    method_variant: str
    attack_name: str
    split: str
    event_id: str
```

```python
@dataclass(frozen=True)
class EncodeResult:
    request_id: str
    cache_key: tuple[str, str]
    latent_tensor: np.ndarray
    output_relpath: Path
    batch_group_id: str
    batch_request_count: int
    effective_batch_size: int
    fallback_count: int
    fallback_reason: str | None
```

### （三）必须提供的函数

```python
def resolve_cross_event_vae_batching_config(runtime_config: dict[str, Any]) -> CrossEventVaeBatchingConfig:
    ...
```

要求：

```text
decode_batch_size 和 encode_batch_size 必须为正整数；
grouping 第一版只允许 same_shape_same_backend；
如果 enabled=false，仍返回合法配置；
任何非法配置必须 ValueError。
```

```python
def group_decode_requests(
    requests: list[DecodeRequest],
    *,
    vae_metadata: dict[str, Any],
) -> list[list[DecodeRequest]]:
    ...
```

分组键至少包含：

```text
operation = decode；
latent_tensor.shape；
target_resolution；
fps；
vae_backend_name；
vae_backend_version；
device；
dtype；
runtime_impl。
```

```python
def group_encode_requests(
    requests: list[EncodeRequest],
    *,
    vae_metadata: dict[str, Any],
) -> list[list[EncodeRequest]]:
    ...
```

分组键至少包含：

```text
operation = encode；
video_frames.shape；
vae_backend_name；
vae_backend_version；
device；
dtype；
runtime_impl。
```

```python
def run_decode_request_batch(
    requests: list[DecodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
) -> list[DecodeResult]:
    ...
```

实现逻辑：

```text
1. 按 config.decode_batch_size 切块；
2. 对每个 chunk 取 latent_tensor；
3. 沿 frame 维 concat：np.concatenate([req.latent_tensor for req in chunk], axis=0)；
4. 调用 vae_runtime_backend.decode_video(concat_latents, config={"target_resolution": target_resolution})；
5. 按每个 request 的 frame_count split；
6. 返回 DecodeResult；
7. 如果发生 OOM / RuntimeError 且 fallback_on_oom=true，则递归或循环降级 chunk size；
8. 如果 batch_size 已为 1 仍失败，则重新抛出异常。
```

```python
def run_encode_request_batch(
    requests: list[EncodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
) -> list[EncodeResult]:
    ...
```

实现逻辑：

```text
1. 按 config.encode_batch_size 切块；
2. 沿 frame 维 concat：np.concatenate([req.video_frames for req in chunk], axis=0)；
3. 调用 vae_runtime_backend.encode_video(concat_video_frames)；
4. 按每个 request 的 frame_count split；
5. 返回 EncodeResult；
6. OOM 时降级 batch size。
```

### （四）OOM 识别

新增函数：

```python
def is_probable_cuda_oom(exc: BaseException) -> bool:
    ...
```

识别字符串：

```text
CUDA out of memory
out of memory
CUBLAS_STATUS_ALLOC_FAILED
CUDA error: out of memory
```

注意：只有 `fallback_on_oom=true` 且 `is_probable_cuda_oom(exc)=true` 时才降级；其他异常应直接抛出，避免掩盖真实错误。

---

## 六、修改 `runner.py`

### （一）新增 runner 状态

在 `RealVideoVaeLatentRunner.__init__()` 中新增：

```python
self._cross_event_vae_batching_config = CrossEventVaeBatchingConfig(... default disabled ...)
self._cross_event_vae_batching_trace: list[dict[str, Any]] = []
```

或在 `run()` 中解析后传递给 `_run_method_variant()` 和 `_run_event_subset()`。

### （二）在 `run()` 中解析配置

当前 `run()` 已经加载：

```python
runtime_config_overrides = self._load_runtime_config(runtime_config_path)
```

新增逻辑：

```python
if cross_event_vae_batching_enabled CLI is not None:
    runtime_config_overrides["cross_event_vae_batching_enabled"] = bool(...)
...

cross_event_config = resolve_cross_event_vae_batching_config(runtime_config_overrides)
```

这里必须遵循当前 runner 真实顺序：先 `_load_runtime_config(runtime_config_path)`，再叠加 CLI 显式参数。不要新增“从 runtime profile JSON 或 backend config 继续取默认 batching 字段”的逻辑。

如果：

```python
cross_event_config.enabled and self._event_worker_count != 1
```

则：

```python
raise ValueError("cross-event VAE batching requires worker_count == 1 in the first governed implementation")
```

### （三）写入 runtime manifest

当前 runtime manifest 中已有 `runtime_config_overrides` 和 worker / profile 信息。新增：

```json
{
  "cross_event_vae_batching": {
    "enabled": true,
    "decode_batch_size": 4,
    "encode_batch_size": 4,
    "grouping": "same_shape_same_backend",
    "fallback_on_oom": true,
    "write_trace": true
  }
}
```

### （四）新增 batching trace 输出

在 run root 下写入：

```text
runtime_profile/cross_event_vae_batching_trace.jsonl
runtime_profile/cross_event_vae_batching_summary.json
```

每条 trace 至少包含：

```json
{
  "operation": "decode",
  "batch_group_id": "decode:...",
  "request_count": 4,
  "effective_batch_size": 4,
  "fallback_count": 0,
  "fallback_reason": null,
  "method_variant": "tubelet_sync",
  "split": "test",
  "runtime_profile": "formal"
}
```

summary 至少包含：

```json
{
  "enabled": true,
  "decode_request_count": 100,
  "encode_request_count": 100,
  "decode_batch_count": 25,
  "encode_batch_count": 25,
  "decode_fallback_count": 0,
  "encode_fallback_count": 0,
  "max_decode_effective_batch_size": 4,
  "max_encode_effective_batch_size": 4
}
```

### （五）重构 `_process_event_plan_entries()`

当前 `_process_event_plan_entries()` 是单 loop，流程为：

```text
for event:
  build source
  embed
  decode
  attack
  reencode
  detect
  metrics
  record
```

必须改为保留 sequential 路径，同时新增 batched 路径：

```python
if not cross_event_config.enabled:
    return self._process_event_plan_entries_sequential(...)
return self._process_event_plan_entries_with_cross_event_vae_batching(...)
```

第一步：把当前 `_process_event_plan_entries()` 主体改名为：

```python
def _process_event_plan_entries_sequential(...):
    # 原逻辑，尽量不改
```

第二步：新增：

```python
def _process_event_plan_entries_with_cross_event_vae_batching(...):
    ...
```

### （六）batched 路径具体控制流

`_process_event_plan_entries_with_cross_event_vae_batching()` 分 6 个阶段。

#### 阶段 1：构造 event contexts

新增内部 dataclass 或普通 dict：

```python
@dataclass
class EventRuntimeContext:
    event_plan_entry: EventPlanEntry
    source_sample: LatentSample
    working_sample: LatentSample
    attacked_sample: LatentSample | None
    watermarked_latent_metadata: dict[str, str] | None
    event_artifact_digest: str
    decoded_artifact_digest: str
    decoded_video_relpath: Path
    attacked_video_relpath: Path
    reencoded_latent_relpath: Path
    video_fps: int
    video_resolution: tuple[int, int]
    decoded_cache_key: tuple[str, str, str]
    attack_params: dict[str, Any]
```

这个阶段只执行：

```text
source_sample build；
method.embed；
watermarked latent copy；
attack params materialization；
路径与 cache_key 计算。
```

不得执行 VAE decode / encode。

#### 阶段 2：批量 decode

对所有 contexts 创建 DecodeRequest。跳过以下情况：

```text
cache 中已有 decoded metadata；
output_path 已存在；
```

已有 artifact 的情况仍走现有 `_build_video_artifact_metadata_from_path()` 和 `_get_cached_video_tensor()`。

对缺失的 decoded videos：

```text
加载 latent tensor；
构造 DecodeRequest；
group_decode_requests；
run_decode_request_batch；
逐个 _write_video_artifact；
更新 decoded_video_cache；
更新 decoded_video_tensor_cache；
保存 decoded_video_metadata 到 context。
```

注意：写 mp4 仍 per-event，不要 batch 写视频。

#### 阶段 3：per-event attack materialization

第一版 batched 路径只覆盖 mp4 runtime 下的现有 attack 逻辑：

```text
no_attack：attacked = decoded；
apply_video attack：逐 event 调用；
apply_frames / temporal attack：逐 event 调用。
```

这一步不做 batch。

补充约束：

```text
如果当前 run 不满足 mp4 runtime 条件，不要在 batched 路径里新增一套未验证的 tensor_scaffold attack 语义；
应在 run 启动时 fail-fast，或整次回退到 sequential 路径。
```

#### 阶段 4：批量 re-encode

对所有 contexts 创建 EncodeRequest。跳过以下情况：

```text
reencoded_cache 已存在；
reencoded_latent output_path 已存在。
```

对缺失的 reencoded latents：

```text
从 attacked_video_tensor_cache 或 attacked_video_metadata 读取 frames；
构造 EncodeRequest；
group_encode_requests；
run_encode_request_batch；
逐个 write_float_tensor_npy；
计算 digest；
更新 reencoded_cache；
保存 reencoded_latent_metadata 到 context。
```

写 latent 仍 per-event。

这里的前提也是：batched path 只处理 mp4 runtime 下已经 materialize 完成的 attacked_video_tensor。tensor_scaffold 路径由上一条固定策略处理，不在第一版 batched encode 范围内扩展语义。

#### 阶段 5：per-event detect / metrics / record

复用原 sequential 逻辑：

```text
_build_reencoded_sample；
method.detect；
_load_metric_frame_pair；
build_real_video_quality_metrics_payload；
build_real_video_temporal_metrics_payload；
event_score_record construction。
```

这里必须确保最终 record 与 sequential 路径字段一致，只新增 batch diagnostic 字段。

#### 阶段 6：排序返回

最后：

```python
records.sort(key=lambda record: str(record.get("event_id", "")))
return records
```

保证 records 顺序稳定。

### （七）机制 trace 新增字段

每条 event record 的 `mechanism_trace` 中最多新增最小诊断字段：

```json
{
  "cross_event_vae_batching_enabled": true,
  "cross_event_vae_decode_effective_batch_size": 4,
  "cross_event_vae_encode_effective_batch_size": 4,
  "cross_event_vae_batching_fallback_count": 0,
  "cross_event_vae_batching_fallback_reason": null
}
```

如果 batching disabled，也写：

```json
{
  "cross_event_vae_batching_enabled": false
}
```

批次级 group_id、request_count、逐 chunk fallback 明细应放在 `runtime_profile/cross_event_vae_batching_trace.jsonl` 与 summary 中，不要把这些高基数字段扩散进 records。这样 mechanism audit 可以确认运行模式，但不得把这些字段作为机制分数。

---

## 七、`diffusers_autoencoder_kl_framewise.py` 修改要求

当前 backend 已经可以处理 `[F,C,H,W]` 和 `[F,H,W,3]` 的 frame batch，不需要重写模型加载逻辑。

建议只做两个小增强：

### （一）增加显式 metadata

`backend_metadata()` 新增：

```json
{
  "supports_cross_event_frame_batching": true,
  "frame_batch_axis": 0,
  "cross_event_batching_semantics": "caller_may_concatenate_same_shape_video_or_latent_frames"
}
```

### （二）增加输入 batch 边界检查

在 `encode_video()` 和 `decode_video()` 中，当输入帧数为 0 时已经会失败。建议错误信息更明确：

```text
encode_video requires at least one frame after cross-event concatenation
decode_video requires at least one latent frame after cross-event concatenation
```

不要求新增 `encode_videos()` 或 `decode_latents()` 多视频 API。第一版由 runner batching layer 负责 concat / split，backend 仍保持 framewise API。

---

## 八、notebook 与 workflow 修改

### （一）`paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py`

更新以下函数签名：

```python
def _build_probe_runner_command(...,
    cross_event_vae_batching_enabled: bool | None = None,
    cross_event_vae_decode_batch_size: int | None = None,
    cross_event_vae_encode_batch_size: int | None = None,
    ...
) -> list[str]:
```

如果参数不为 None，追加 CLI：

```text
--cross-event-vae-batching-enabled <true|false>
--cross-event-vae-decode-batch-size <int>
--cross-event-vae-encode-batch-size <int>
```

同步更新：

```text
run_probe_runner()
run_probe_method_variant_splits()
_build_probe_runner_command()
```

注意：当前真实 helper 名称是 `run_probe_stage2_mechanism_calibration()`，不是 `run_stage2_mechanism_calibration_from_notebook()`。第一版不要求给该 helper 新增一组平行 CLI 参数；stage2 calibration 应通过既有 `runtime_config_path` 继承 batching 设置。

### （二）`paper_workflow/run_real_video_vae_latent_probe.ipynb`

当前 notebook 已使用 `NOTEBOOK_MANUAL_CONFIG` 与 `NOTEBOOK_MANUAL_ENV_MAP` 承载用户配置。第一版应扩展现有配置容器，而不是另起一组顶层常量。建议新增：

```python
NOTEBOOK_MANUAL_CONFIG.update({
  "cross_event_vae_batching_enabled": False,
  "cross_event_vae_decode_batch_size": 4,
  "cross_event_vae_encode_batch_size": 4,
})
```

并允许环境变量覆盖：

```python
NOTEBOOK_MANUAL_ENV_MAP.update({
  "cross_event_vae_batching_enabled": "TSTW_CROSS_EVENT_VAE_BATCHING_ENABLED",
  "cross_event_vae_decode_batch_size": "TSTW_CROSS_EVENT_VAE_DECODE_BATCH_SIZE",
  "cross_event_vae_encode_batch_size": "TSTW_CROSS_EVENT_VAE_ENCODE_BATCH_SIZE",
})
```

注意：默认仍为 False。

在 runtime config 写入时加入：

```python
runtime_config_payload.update({
  "cross_event_vae_batching_enabled": NOTEBOOK_MANUAL_CONFIG["cross_event_vae_batching_enabled"],
  "cross_event_vae_decode_batch_size": NOTEBOOK_MANUAL_CONFIG["cross_event_vae_decode_batch_size"],
  "cross_event_vae_encode_batch_size": NOTEBOOK_MANUAL_CONFIG["cross_event_vae_encode_batch_size"],
})
```

notebook 推荐路径是把 batching 相关键写入 runtime_config，再通过既有 `runtime_config_path` 交给 runner。只有在需要覆盖 runtime_config 的 direct helper 测试里，才建议显式透传 CLI 参数，例如：

```python
probe_workflow.run_probe_runner(
    ...,
  cross_event_vae_batching_enabled=NOTEBOOK_MANUAL_CONFIG["cross_event_vae_batching_enabled"],
  cross_event_vae_decode_batch_size=NOTEBOOK_MANUAL_CONFIG["cross_event_vae_decode_batch_size"],
  cross_event_vae_encode_batch_size=NOTEBOOK_MANUAL_CONFIG["cross_event_vae_encode_batch_size"],
)
```

stage2 calibration helper 不需要新增并列 notebook 接口；只要它继续接收 `runtime_config_path`，就可以继承同一份 batching 配置。

### （三）notebook 显示输出

runner 完成后，notebook 应显示：

```text
runtime_profile/cross_event_vae_batching_summary.json
```

如果文件不存在且 batching disabled，可以显示：

```json
{"enabled": false, "reason": "cross_event_vae_batching_disabled"}
```

---

## 九、等价性测试要求

### （一）新增 `tests/integration/test_cross_event_vae_batching_equivalence.py`

测试逻辑：

```text
1. 使用 debug_real_video profile；
2. sequential run：cross_event_vae_batching_enabled=false；
3. batched run：cross_event_vae_batching_enabled=true，decode_batch_size=2，encode_batch_size=2，worker_count=1；
4. 读取两个 run 的 records/event_scores.jsonl；
5. 按 event_id 对齐；
6. 比较 per-event records、threshold 数量、artifact manifest 语义与可选的 checker / audit helper 输出。
```

必须完全一致的字段：

```text
event_id
sample_id
split
sample_role
method_variant
attack_name
decision
failure_reason
disabled_evidence
```

并且需要额外比较：

```text
records 条数；
thresholds 条数；
artifact_manifest 中 artifact_kind roster；
tables 行数。
```

允许容差比较的字段：

```text
evidence_scores 中的数值字段
quality_metrics 数值字段
temporal_metrics 数值字段
```

容差：

```text
absolute_tolerance = 1e-5
relative_tolerance = 1e-4
```

注意：视频文件 digest 不要求完全一致，因为 mp4 编码可能存在非 bitwise 稳定性；但 metadata 必须一致：

```text
container
frame_count
fps
height
width
```

latent `.npy` digest 在 mock backend 下应一致；在真实 diffusers + fp16 下可不要求 bitwise digest，但 score 必须在容差内。

如果测试还要比较 checker / mechanism audit 结果，必须显式调用：

```text
probe_workflow.check_probe_outputs()
probe_workflow.run_probe_stage2_mechanism_audit()
```

并在 helper 返回摘要层比较 pass/fail 与关键布尔字段；不要把 `Stage2ImplementationDecision` 或 `Stage2MechanismDecision` 当成 bare runner 直接写出的字段来断言。

### （二）新增 `tests/integration/test_cross_event_vae_batching_artifact_contract.py`

验证：

```text
batched run 仍生成：
records/event_scores.jsonl
thresholds/thresholds.json
tables/*.csv
reports/vae_latent_probe_report.md
artifacts/artifact_manifest.json
runtime_profile/cross_event_vae_batching_summary.json
runtime_profile/cross_event_vae_batching_trace.jsonl
```

验证 artifact manifest 中：

```text
source_video
encoded_latent
watermarked_latent
decoded_video
attacked_video
reencoded_latent
```

数量不低于 sequential run。

### （三）新增 `tests/integration/test_cross_event_vae_batching_fallback.py`

使用 fake VAE backend 或 monkeypatch 让 batch_size > 1 时抛出 `RuntimeError("CUDA out of memory")`，batch_size = 1 时成功。

验证：

```text
runner 不失败；
cross_event_vae_batching_summary.json 中 fallback_count > 0；
mechanism_trace 中 fallback_reason 包含 cuda_oom；
records 仍完整生成。
```

### （四）新增 `tests/functional/test_cross_event_vae_batching_config.py`

验证：

```text
resolve_cross_event_vae_batching_config() 默认 disabled；
非法 batch size 抛 ValueError；
非法 grouping 抛 ValueError；
CLI / runtime config override 优先级正确。
```

### （五）更新 notebook contract 测试

更新：

```text
tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py
```

新增断言：

```text
notebook 含 cross_event_vae_batching_enabled 配置键；
notebook 含 cross_event_vae_decode_batch_size 配置键；
notebook 含 cross_event_vae_encode_batch_size 配置键；
notebook 支持 TSTW_CROSS_EVENT_VAE_BATCHING_ENABLED 环境变量；
notebook 调用 run_probe_runner 时传入 cross-event VAE batching 参数；
notebook 默认 cross_event_vae_batching_enabled = False。
```

---

## 十、运行诊断与结果解释

### （一）runtime_profile 产物

新增产物：

```text
runtime_profile/cross_event_vae_batching_trace.jsonl
runtime_profile/cross_event_vae_batching_summary.json
```

这些产物应进入 package，但不得进入 records / tables 方法证据。

### （二）packager

当前以下 packager 已包含 `runtime_profile/**`：

```text
scripts/package_results/package_real_video_vae_latent_outputs.py
scripts/package_results/package_real_video_vae_latent_tar_zst.py
```

本补丁不得破坏该行为；新增 batching summary / trace 只需继续落在 `runtime_profile/` 下即可被现有 packager 带出。

### （三）field registry

field registry 只覆盖 governed field。第一版应控制新增字段数量：

```text
如果 records/mechanism_trace 中写入 cross_event_vae_batching_enabled，则登记该字段；
如果 records/mechanism_trace 中还写入 effective_batch_size 或 fallback 字段，再逐项登记；
runtime_profile/cross_event_vae_batching_trace.jsonl 与 summary.json 内部的 trace-only key 不需要为了本补丁引入新的 field_registry category。
```

字段类别应沿用现有 registry 类别，例如 `trace` 或 `protocol`；不要为本补丁新造 `runtime_diagnostic_field` 类别。
不得标记为 method evidence field。

---

## 十一、验收命令

Codex 完成后必须运行：

### （一）默认测试

```bash
PYTHONPATH=. python -m pytest -q
```

### （二）batching 相关测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/functional/test_cross_event_vae_batching_config.py \
  tests/integration/test_cross_event_vae_batching_equivalence.py \
  tests/integration/test_cross_event_vae_batching_artifact_contract.py \
  tests/integration/test_cross_event_vae_batching_fallback.py \
  tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py
```

### （三）阶段 2 关键回归

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/integration/test_real_video_records_schema_smoke.py \
  tests/integration/test_real_video_table_rebuild_smoke.py \
  tests/integration/test_real_video_vae_encode_decode_smoke.py \
  tests/functional/test_mechanism_audit.py \
  tests/constraints/test_mechanism_decision_contract.py
```

### （四）审计

```bash
PYTHONPATH=. python tools/harness/run_all_audits.py
```

### （五）手动 debug run

Sequential golden run：

```bash
RUN_ROOT_SEQ=/tmp/tstw_seq_debug
rm -rf "$RUN_ROOT_SEQ"
PYTHONPATH=. python -m experiments.real_video_vae_latent_probe.runner \
  --run-mode smoke \
  --runtime-profile debug_real_video \
  --run-root "$RUN_ROOT_SEQ" \
  --worker-count 1
```

Batched run：

```bash
RUN_ROOT_BATCH=/tmp/tstw_batch_debug
rm -rf "$RUN_ROOT_BATCH"
PYTHONPATH=. python -m experiments.real_video_vae_latent_probe.runner \
  --run-mode smoke \
  --runtime-profile debug_real_video \
  --run-root "$RUN_ROOT_BATCH" \
  --worker-count 1 \
  --cross-event-vae-batching-enabled true \
  --cross-event-vae-decode-batch-size 2 \
  --cross-event-vae-encode-batch-size 2
```

然后运行 checker：

```bash
PYTHONPATH=. python -m scripts.check_results.check_real_video_vae_latent_outputs \
  --run-root "$RUN_ROOT_BATCH" \
  --run-mode smoke
```

---

## 十二、通过标准

本次变更完成的标准不是“速度变快”，而是：

```text
1. cross-event VAE batching 默认关闭；
2. 启用后 runner 能完成 debug_real_video run；
3. sequential 与 batched run 的 records、tables、decision 在指定容差内等价；
3. sequential 与 batched run 的 records、thresholds、tables 在指定容差内等价；
4. batching 只改变 VAE decode / encode 调度，不改变 attack / detect / record 语义；
5. worker_count > 1 与 batching 同时启用时 fail-fast；
6. OOM fallback 可以退化到 batch_size=1；
7. notebook 可以通过配置启用 batching，但默认关闭；
8. runtime_profile 中有 batching trace 与 summary；
9. 若显式执行 formal checker 和 mechanism audit，其 helper 输出语义未改变；
10. 默认测试、batching 测试、阶段 2 关键回归和总审计全部通过。
```

不得把以下情况当作通过：

```text
1. batched run 更快，但 records 与 sequential 不等价；
2. 为了等价性跳过部分 event；
3. 为了速度不写 decoded / attacked / reencoded artifact；
4. 为了速度不计算 quality / temporal metrics；
5. 修改 threshold 或 mechanism gate 让结果看起来一致；
6. 用 batching 结果反向改变 Stage2MechanismDecision gate。
```

---

## 十三、建议实现顺序

建议 Codex 按以下顺序实现：

```text
P0：新增 vae_batching.py，仅实现 config、request/result dataclass、grouping、concat/split batch decode/encode；
P1：为 vae_batching.py 添加功能测试；
P2：runner 中新增 config 解析、CLI 参数、worker_count guard、runtime manifest 字段；
P3：把原 _process_event_plan_entries() 重命名为 sequential 路径；
P4：实现 _process_event_plan_entries_with_cross_event_vae_batching()；
P5：写 cross_event_vae_batching_trace.jsonl 与 summary.json；
P6：添加 equivalence / artifact / fallback 测试；
P7：更新 notebook workflow helper 与 notebook；
P8：更新 docs/field_registry.md 和 gpu_runtime_optimization_governance.md；
P9：跑完整验收。
```

如遇时间不足，至少完成 P0–P6。Notebook 接入可以作为后续小 patch，但 runner 的等价性测试必须优先完成。

---

## 十四、最终目标表述

完成本次变更后，项目应支持两种受治理运行模式：

```text
sequential runner：默认模式，作为 golden reference；
cross-event VAE batched runner：可选加速模式，用于 Stage2 机制选参和 calibration run。
```

两者的差异只能体现在：

```text
runtime_profile/cross_event_vae_batching_trace.jsonl
runtime_profile/cross_event_vae_batching_summary.json
运行时间与 GPU 利用率
```

不应体现在：

```text
records 数量；
evidence score 语义；
decision 语义；
threshold 语义；
mechanism audit 语义；
formal checker 语义。
```
