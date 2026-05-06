# 方法机制：面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印框架

## 一、项目目标与论文定位

### （一）总体目标

本文目标不是提出一个普通视频水印方法，也不是将图像水印逐帧迁移到视频生成模型中，而是提出一种面向 DiT / Flow Matching 视频生成模型的 **时空同步轨迹水印框架**。该框架将水印证据从逐帧初始噪声扩展到跨帧 latent tubelet 与采样轨迹统计量，并通过 temporal PRC synchronization 实现对时间攻击和局部片段检测的鲁棒恢复。

本文希望最终形成一个能够支撑顶会投稿的方法体系，其核心要求包括：

1. 具有明确的算法原语，而不是多个工程模块的经验拼接；
2. 具有清晰的统计判决理论，尤其是在 fixed low-FPR protocol 下验证水印检测可靠性；
3. 具有不可替代的机制贡献，即每个 evidence 分支都对应一个明确失效模式和恢复机制；
4. 能够在 clean negative、attacked negative、watermarked positive 与 attacked positive 四类样本上进行统一验证；
5. 能够通过系统消融证明 tubelet evidence、trajectory evidence 与 synchronization evidence 对最终鲁棒性具有独立贡献。

### （二）论文问题定义

给定一个视频生成模型 \(G_\theta\)，其在 latent space 中生成视频表示：

\[
z \in \mathbb{R}^{F\times C\times H\times W},
\]

其中，\(F\) 表示 latent frame 数，\(C\) 表示通道数，\(H,W\) 表示 latent 空间分辨率。对于 DiT / Flow Matching 视频生成模型，\(z\) 通常进一步被划分为时空 token 或 spacetime patch / tubelet 结构。

本文研究如下问题：

> 如何在不显著损害视频质量和时序一致性的前提下，将水印信息编码到视频 latent tubelet 与 Flow Matching 采样轨迹中，并在未知时间攻击、空间攻击和局部片段检测条件下，通过密钥条件统计检验可靠判断视频是否包含水印。

该问题不同于传统图像水印，也不同于普通视频后处理水印。其关键困难在于：

1. 视频水印面临 temporal crop、frame dropping、speed change、frame insertion、segment shuffle 等时间攻击；
2. 局部片段检测中，检测器无法知道被检测片段对应原始水印序列的哪个时间位置；
3. DiT / Flow Matching 视频生成模型的水印不能只依赖最终像素或单帧 latent，而应利用其时空 token 表征与采样过程结构；
4. 检测结果必须在低假阳性率条件下成立，不能依赖事后调阈值或攻击类型特定阈值。

---

## 二、核心方法论

### （一）从逐帧水印转向时空 tubelet 水印

逐帧水印的基本假设是每一帧独立承载水印信号：

\[
c_f \rightarrow z_f。
\]

该假设在图像水印或短视频弱攻击条件下可以成立，但在视频生成水印中存在结构性缺陷：

1. frame dropping 会破坏水印索引；
2. temporal crop 会导致检测端不知道起始帧偏移；
3. speed change 会改变帧间采样关系；
4. local clip detection 会使完整消息不可见；
5. frame-wise code 难以利用视频中的时序冗余。

因此，本文将基本承载单元从 frame 扩展为 latent tubelet：

\[
g=(\tau,i,j),
\]

其中，\(\tau\) 表示时间 tubelet 索引，\(i,j\) 表示空间 tubelet 位置。每个 tubelet 覆盖 \(L_t\) 个 latent frame 与一个局部空间区域：

\[
z_g \in \mathbb{R}^{L_t\times C\times P_h\times P_w}。
\]

水印码不再绑定到单帧，而绑定到跨帧 tubelet。该设计使水印天然具有跨帧冗余、局部片段可检测性和对时间攻击的恢复空间。

### （二）从静态 latent 证据转向采样轨迹证据

普通扩散水印多依赖初始噪声或最终图像 / 视频 latent 的统计可检测性。对于 Flow Matching 视频生成模型，其生成过程可以表示为连续向量场：

\[
\frac{dz_t}{dt}=v_\theta(z_t,t,c),
\]

其中，\(t\in[0,1]\)，\(c\) 表示文本条件或其他生成条件。该表述说明，生成样本不仅由起点和终点决定，也由采样轨迹中的速度场统计量决定。

因此，本文引入 Flow Matching trajectory statistic，将水印检测扩展为：

\[
\text{initial / tubelet evidence}+\text{trajectory evidence}。
\]

trajectory evidence 的作用不是替代 tubelet evidence，而是在 tubelet evidence 受到压缩、噪声或局部攻击削弱时，提供与生成过程相关的补充证据。

### （三）从重复冗余转向 temporal synchronization

视频水印中的关键问题不是简单增加 payload 冗余，而是恢复攻击后的时间对齐关系。设原始时间索引为 \(\tau\)，攻击后观测索引为 \(\hat{\tau}\)，二者之间存在未知映射：

\[
\pi:\hat{\tau}\mapsto \tau。
\]

temporal crop 对应时间偏移，frame dropping 对应非均匀缺失，speed change 对应尺度变化，local clip detection 对应只观察到 \(\pi\) 的局部片段。因此，本文将 synchronization evidence 定义为时间对齐恢复问题，而不是普通同步头或重复码。

---

## 三、方法核心：三个算法原语

本文方法不应被写成“tubelet 分数、trajectory 分数和 sync 分数的工程融合”。更合理的算法化定义是：

> 本文提出一种 temporal-synchronized tubelet trajectory code，将 payload 编码、时间同步恢复和 Flow Matching trajectory statistic 统一为 fixed low-FPR 条件下的结构化统计检测问题。

具体包含三个算法原语。

---

### （一）算法原语 1：Temporal-Synchronized Tubelet Code

#### 1. Tubelet 划分

给定 latent video：

\[
z\in\mathbb{R}^{F\times C\times H\times W}，
\]

将其划分为 tubelet 集合：

\[
\mathcal{G}=\{g=(\tau,i,j)\}。
\]

每个 tubelet 对应局部张量：

\[
z_g\in\mathbb{R}^{L_t\times C\times P_h\times P_w}。
\]

其中，\(L_t\) 是时间长度，\(P_h,P_w\) 是空间 patch 尺寸。

#### 2. 密钥方向生成

对每个 tubelet 由密钥生成单位方向：

\[
u_g=\mathrm{PRG}(K_{\mathrm{dir}},g),\quad \|u_g\|_2=1。
\]

该方向定义检测时的投影统计量：

\[
a_g=\langle z_g,u_g\rangle。
\]

#### 3. Payload code

给定用户消息或水印身份 \(m\)，生成 payload 符号：

\[
c^{\mathrm{pay}}_g=\mathrm{PRC}(K_{\mathrm{pay}},m,g),\quad c^{\mathrm{pay}}_g\in\{-1,+1\}。
\]

payload code 负责承载身份信息或来源标识。

#### 4. Temporal synchronization code

对每个时间 tubelet 生成同步符号：

\[
c^{\mathrm{sync}}_\tau=\mathrm{SyncCode}(K_{\mathrm{sync}},\tau),\quad c^{\mathrm{sync}}_\tau\in\{-1,+1\}。
\]

同步码应具有以下性质：

1. 自相关峰值尖锐；
2. 不同密钥间互相关低；
3. 局部片段内仍具有可检测同步结构；
4. 搜索空间扩大时能够通过 calibration negative 控制 FPR。

可探索的同步码包括 m-sequence、Gold code、Barker-like code、Zadoff-Chu-like sequence 或密钥生成的低互相关二元序列。

#### 5. Joint tubelet code

最终 tubelet code 定义为：

\[
c_g=c^{\mathrm{pay}}_g\cdot c^{\mathrm{sync}}_\tau。
\]

该定义将 payload 与 synchronization 解耦：payload 负责身份编码，sync 负责时间对齐恢复。

#### 6. Projection-margin embedding

第一阶段建议采用 projection-margin embedding：

\[
c_g\langle z_g,u_g\rangle \ge \alpha。
\]

若不满足约束，则沿密钥方向做最小修正：

\[
z'_g=z_g+\left(\alpha-c_g\langle z_g,u_g\rangle\right)c_g u_g。
\]

该嵌入方式具有三个优点：

1. 形式简单，便于机制验证；
2. 与 tubelet 投影检测严格对应；
3. 可直接控制 margin \(\alpha\) 与 distortion 的关系。

后续阶段可进一步探索 distribution-preserving projection、rejection sampling、quantile-preserving transform 或采样过程约束，以降低分布偏移。

---

### （二）算法原语 2：Temporal PRC Synchronization

#### 1. 攻击后的时间对齐问题

攻击后观测 latent 记为 \(\hat{z}\)。检测端无法直接知道 \(\hat{z}_{\hat{\tau}}\) 对应原始时间索引 \(\tau\)。因此，需要估计：

\[
\pi^\ast=\arg\max_{\pi\in\Pi}S_{\mathrm{sync}}(\pi)。
\]

其中，\(\Pi\) 表示候选时间变换集合。

#### 2. 同步响应计算

先对每个观测时间 tubelet 计算聚合响应：

\[
\bar{q}_{\hat{\tau}}
=
\frac{1}{|\mathcal{G}_{\hat{\tau}}|}
\sum_{g\in\mathcal{G}_{\hat{\tau}}}
\langle \hat{z}_g,u_g\rangle。
\]

然后计算同步相关：

\[
S_{\mathrm{sync}}(\Delta)
=
\sum_{\hat{\tau}}
\bar{q}_{\hat{\tau}}c^{\mathrm{sync}}_{\hat{\tau}+\Delta}。
\]

如果考虑 speed change，则扩展为：

\[
S_{\mathrm{sync}}(\Delta,\rho)
=
\sum_{\hat{\tau}}
\bar{q}_{\hat{\tau}}c^{\mathrm{sync}}_{\lfloor \rho\hat{\tau}+\Delta\rfloor}。
\]

其中，\(\Delta\) 表示时间偏移，\(\rho\) 表示时间尺度变化。

#### 3. 对齐恢复

检测端选择：

\[
(\Delta^\ast,\rho^\ast)
=
\arg\max_{\Delta,\rho}S_{\mathrm{sync}}(\Delta,\rho)。
\]

随后在恢复的时间对齐关系下计算 payload score：

\[
S_{\mathrm{tubelet}}
=
\frac{1}{|\mathcal{G}|}
\sum_g
c^{\mathrm{pay}}_{\pi^\ast(g)}
\langle \hat{z}_g,u_{\pi^\ast(g)}\rangle。
\]

#### 4. 机制意义

Temporal PRC synchronization 的不可替代性在于：它解决的是 temporal desynchronization，而不是增加普通冗余。若没有该模块，局部片段检测和 temporal crop 后的 payload index 会发生错位，即使每个局部 tubelet 仍含有水印信号，也无法可靠聚合为正确检测结果。

---

### （三）算法原语 3：Flow Matching Trajectory Statistic

#### 1. Flow Matching 采样轨迹

Flow Matching 视频生成模型的采样过程可以表示为：

\[
\frac{dz_t}{dt}=v_\theta(z_t,t,c)。
\]

本文将水印证据从 \(z_1\) 或 \(z_0\) 的静态投影扩展到轨迹上的速度投影统计量。

#### 2. Trajectory-aware detector

在初始阶段，不建议直接修改采样器，而应先构造 trajectory-aware detector。对疑似视频进行近似 inversion 或 partial trajectory reconstruction，得到：

\[
\hat{z}_{t_1},\hat{z}_{t_2},\ldots,\hat{z}_{t_M}。
\]

估计局部速度：

\[
\hat{v}_{m,g}
=
\frac{\hat{z}_{t_{m+1},g}-\hat{z}_{t_m,g}}
{t_{m+1}-t_m}。
\]

定义 trajectory score：

\[
S_{\mathrm{traj}}
=
\frac{1}{|\mathcal{G}|M}
\sum_{g\in\mathcal{G}}
\sum_{m=1}^{M}
c_g
\langle \hat{v}_{m,g},u_g\rangle。
\]

该统计量衡量观测轨迹中的局部速度方向是否与水印 tubelet code 具有一致性。

#### 3. Trajectory-aware embedding

若 trajectory-aware detector 证明有效，则进一步引入采样过程弱约束：

\[
v'_\theta(z_t,t,c)
=
v_\theta(z_t,t,c)
+
\lambda(t)\sum_g c_gP_gu_g。
\]

其中，\(P_g\) 表示 tubelet 局部投影算子，\(\lambda(t)\) 是时间调度函数。建议仅在中间采样阶段启用：

\[
\lambda(t)=0,\quad t\in[0,0.2]\cup[0.8,1]。
\]

该设计避免早期破坏全局语义结构，也避免末期破坏细节纹理。

#### 4. 机制意义

Flow Matching trajectory statistic 的不可替代性在于：它使水印证据与生成过程本身绑定，而不是只依赖最终视频或初始噪声。若 trajectory evidence 能在固定 FPR 下提供独立增益，则可以支撑论文中“面向 Flow Matching 生成机制”的核心贡献。

---

## 四、统计判决理论与 fixed low-FPR protocol

### （一）二元假设检验定义

水印检测被定义为二元假设检验：

\[
H_0:y\sim P_{\mathrm{clean}},
\quad
H_1:y\sim P_{\mathrm{wm}}。
\]

其中，\(H_0\) 表示未水印视频，\(H_1\) 表示水印视频。检测器输出最终统计量：

\[
S_{\mathrm{final}}
=
\mathcal{F}_{\mathrm{calib}}
\left(
S_{\mathrm{tubelet}},
S_{\mathrm{sync}},
S_{\mathrm{traj}}
\right)。
\]

其中，\(\mathcal{F}_{\mathrm{calib}}\) 必须只在 dev / calibration 阶段确定，不能使用 test attacked positive 调整。

### （二）Negative calibration

Calibration negative 必须同时包含 clean negative 与 attacked negative：

\[
\mathcal{D}_{\mathrm{calib-neg}}
=
\mathcal{D}_{\mathrm{clean-neg}}
\cup
\mathcal{A}(\mathcal{D}_{\mathrm{clean-neg}})。
\]

这是因为 synchronization search 会扩大搜索空间，若只用 clean negative 标定阈值，会低估 attacked negative 中的偶然相关峰。

### （三）阈值设定

给定目标假阳性率 \(\alpha\)，阈值定义为：

\[
\eta_\alpha
=
\mathrm{Quantile}_{1-\alpha}
\left(
S_{\mathrm{final}}(\mathcal{D}_{\mathrm{calib-neg}})
\right)。
\]

在 test split 上固定 \(\eta_\alpha\)，报告：

1. clean negative FPR；
2. attacked negative FPR；
3. watermarked positive TPR；
4. attacked positive TPR；
5. local clip TPR；
6. temporal attack TPR；
7. confidence interval；
8. threshold stability。

### （四）多证据融合

初始阶段可采用 calibration-normalized score：

\[
\phi_i=\frac{S_i-\mu_i^{\mathrm{neg}}}{\sigma_i^{\mathrm{neg}}+\epsilon}。
\]

最终分数为：

\[
S_{\mathrm{final}}
=
w_1\phi_{\mathrm{tubelet}}
+
w_2\phi_{\mathrm{sync}}
+
w_3\phi_{\mathrm{traj}}。
\]

但论文表述中不应强调经验加权融合，而应解释为 low-FPR calibrated multi-evidence detector。权重 \(w_i\) 的确定必须满足：

1. 仅在 dev 或 calibration 上确定；
2. 不按 attack type 单独调权重；
3. 不基于 test positive 结果选择最优权重；
4. 所有 ablation 使用同一统计协议。

更严格的后续版本可以探索 likelihood-ratio-style fusion：

\[
S_{\mathrm{final}}
=
\log
\frac{
p(S_{\mathrm{tubelet}},S_{\mathrm{sync}},S_{\mathrm{traj}}\mid H_1)
}{
p(S_{\mathrm{tubelet}},S_{\mathrm{sync}},S_{\mathrm{traj}}\mid H_0)
}。
\]

---

## 五、技术路线与阶段性实现安排

### （一）阶段 0：项目骨架与协议冻结

#### 1. 目标

建立可递进扩展的项目代码骨架，固定 sample role、split、record schema、threshold protocol 与 evidence 接口。

#### 2. 方法

构建如下稳定核心：

1. `LatentBackend`：负责 latent 来源；
2. `WatermarkMethod`：负责 embed / detect；
3. `EvidenceExtractor`：负责 tubelet、sync、trajectory evidence；
4. `ProtocolRunner`：负责 dev / calibration / test；
5. `RecordWriter`：负责 event record、score record 与 threshold record；
6. `ThresholdCalibrator`：负责 fixed low-FPR 阈值设定。

#### 3. 预期结果

阶段 0 输出一个可运行但方法简单的空框架，能够写出统一 records，并跑通 calibration / test 的最小流程。

#### 4. 通过标准

1. 所有实验都能显式标记 split；
2. 所有样本都能标记 sample role；
3. 所有 score 都能写入统一 record；
4. threshold 只由 calibration negative 得到；
5. test 阶段不能修改阈值和融合规则。

---

### （二）阶段 1：Synthetic Video Latent Probe

#### 1. 目标

在受控 synthetic video latent 上验证 temporal-synchronized tubelet code 是否成立。

核心问题：

1. tubelet code 是否优于 frame-wise code；
2. temporal synchronization 是否提升 temporal crop、frame dropping 与 local clip detection；
3. attacked negative FPR 是否可控；
4. tubelet length、sync length、clip length 与检测性能之间是否存在可解释关系。

#### 2. 方法

生成 synthetic latent：

\[
z\sim\mathcal{N}(0,I),\quad z\in\mathbb{R}^{F\times C\times H\times W}。
\]

对比三种方法：

1. Frame-PRC；
2. Tubelet-only；
3. Tubelet+Sync。

攻击包括：

1. no attack；
2. temporal crop；
3. frame dropping；
4. speed change；
5. local clip；
6. latent Gaussian noise。

#### 3. 预期结果

预期结果为：

1. Tubelet-only 在时间攻击下优于 Frame-PRC；
2. Tubelet+Sync 在 local clip detection 下显著优于 Tubelet-only；
3. attacked negative FPR 不因 sync search 明显失控；
4. local clip 越短，TPR 下降越明显，但趋势平滑；
5. \(L_t>1\) 相比 \(L_t=1\) 有稳定收益。

#### 4. 需要探索的实验项

1. \(L_t\in\{1,2,4,8,16\}\)；
2. sync code 长度与周期；
3. offset search 与 scale search 的搜索范围；
4. margin \(\alpha\) 与 latent distortion；
5. target FPR 取 \(10^{-2},10^{-3},10^{-4}\) 时的稳定性。

#### 5. 失败判定

若 Tubelet+Sync 无法在 fixed low-FPR 下优于 Frame-PRC，则说明 temporal-synchronized tubelet code 尚未成立，不应进入真实视频模型阶段。

---

### （三）阶段 2：Real Video VAE Latent Probe

#### 1. 目标

验证阶段 1 的机制在真实视频 latent 中是否仍成立，并评估视频质量与时序一致性。

#### 2. 方法

对真实视频 \(x\) 进行 VAE 编码：

\[
z=E_{\mathrm{VAE}}(x)。
\]

在 \(z\) 上执行 tubelet embedding，并通过 decoder 生成水印视频：

\[
x'=D_{\mathrm{VAE}}(z')。
\]

检测时对攻击后视频重新编码：

\[
\hat{z}=E_{\mathrm{VAE}}(\hat{x})。
\]

#### 3. 攻击矩阵

新增真实视频攻击：

1. H.264 / H.265 compression；
2. spatial resize；
3. crop-resize；
4. Gaussian noise；
5. blur；
6. temporal crop；
7. frame dropping；
8. speed change；
9. local clip detection。

#### 4. 预期结果

预期证明：

1. Tubelet+Sync 在真实视频 latent 下仍优于 Frame-PRC；
2. temporal synchronization 能提升 local clip TPR；
3. attacked negative FPR 仍可由 calibration negative 控制；
4. 视频质量下降可控；
5. 时序一致性不出现明显 flicker。

#### 5. 需要探索的实验项

1. 逐帧 VAE 与 video VAE 的差异；
2. latent normalization 是否必要；
3. carrier tubelet 是否应避开高运动区域或高语义敏感区域；
4. H.264 / H.265 对 tubelet 投影的破坏程度；
5. temporal consistency metric 与水印强度之间的关系。

#### 6. 失败判定

若真实 VAE latent 中检测性能显著低于 synthetic latent，则需优先分析分布落差、VAE 编码噪声、视频压缩攻击和 tubelet carrier 选择，而不是直接进入 Flow Matching 阶段。

---

### （四）阶段 3：Flow Matching Trajectory Statistic Probe

#### 1. 目标

验证 trajectory evidence 是否能提供独立于 tubelet evidence 与 sync evidence 的补充判别力。

#### 2. 方法

先做 trajectory-aware detector，而不是直接改采样器。通过近似 inversion 得到多时间点 latent：

\[
\hat{z}_{t_1},\hat{z}_{t_2},\ldots,\hat{z}_{t_M}。
\]

计算 velocity projection statistic：

\[
S_{\mathrm{traj}}
=
\frac{1}{|\mathcal{G}|M}
\sum_{g,m}
c_g
\langle
\hat{v}_{m,g},
u_g
\rangle。
\]

#### 3. 方法变体

至少包括：

1. Tubelet-only；
2. Tubelet+Sync；
3. Tubelet+Trajectory；
4. Trajectory-only；
5. Full。

#### 4. 预期结果

理想结果为：

1. \(S_{\mathrm{traj}}\) 在 positive 与 negative 之间具有统计分离；
2. Tubelet+Trajectory 优于 Tubelet-only；
3. Full 优于 Tubelet+Sync；
4. trajectory score 与 tubelet score 的相关性不是接近 1；
5. trajectory evidence 的运行开销可量化。

#### 5. 需要探索的实验项

1. inversion 方法；
2. trajectory 采样点 \(M\)；
3. velocity projection 与 displacement projection 的差异；
4. trajectory score 与 tubelet score 的相关性；
5. trajectory score 在不同攻击下的稳定性。

#### 6. 失败判定

若 trajectory score 与 tubelet score 高度冗余，或在 fixed low-FPR 下无边际增益，则不应将 trajectory evidence 强写为核心贡献。此时可将论文主线收敛到 temporal-synchronized tubelet code。

---

### （五）阶段 4：Trajectory-Aware Embedding for DiT / Flow Matching

#### 1. 目标

将水印机制从 latent post-hoc embedding 推进到 Flow Matching sampling-time weak constraint，使方法真正绑定 DiT / Flow Matching 生成过程。

#### 2. 方法

在 Flow Matching 速度场上加入弱约束：

\[
v'_\theta(z_t,t,c)
=
v_\theta(z_t,t,c)
+
\lambda(t)\sum_g c_gP_gu_g。
\]

其中，\(\lambda(t)\) 只在中间采样阶段非零。

#### 3. 预期结果

预期证明：

1. trajectory-aware embedding 增强 \(S_{\mathrm{traj}}\)；
2. Full 方法在 temporal attack 与 compression attack 下优于只做 initial tubelet embedding；
3. 视频质量下降可控；
4. 不同 prompt 和 seed 下趋势稳定；
5. 该约束不会引入明显 motion artifact。

#### 4. 需要探索的实验项

1. \(\lambda(t)\) 的时间调度；
2. \(\lambda\) 强度与视频质量的权衡；
3. 哪些采样步最适合施加水印约束；
4. 对文本语义一致性和 motion consistency 的影响；
5. 是否需要 content-aware 或 motion-aware carrier selection。

#### 5. 失败判定

若 trajectory-aware embedding 破坏视频质量，或相比 trajectory-aware detector 没有增益，则应将该模块降级为探索性实验，不应作为主论文强主张。

---

### （六）阶段 5：Full Paper Protocol

#### 1. 目标

冻结完整论文实验协议，形成可投稿的主表、消融表、攻击曲线、质量表、运行开销表与机制分析。

#### 2. 实验协议

必须包含：

1. dev / calibration / test 三段式划分；
2. clean negative、attacked negative、watermarked positive、attacked positive 四类样本；
3. fixed low-FPR threshold；
4. 统一 attack matrix；
5. 统一 ablation variants；
6. 统一 baseline comparison。

#### 3. 主表

主表至少包括：

1. clean negative FPR；
2. attacked negative FPR；
3. clean positive TPR；
4. attacked positive TPR；
5. local clip TPR；
6. quality score；
7. runtime overhead。

#### 4. 消融表

必须报告：

\[
\Delta_{\mathrm{tubelet}}
=
\mathrm{TPR}(\mathrm{Tubelet-only})
-
\mathrm{TPR}(\mathrm{Frame-PRC})。
\]

\[
\Delta_{\mathrm{sync}}
=
\mathrm{TPR}(\mathrm{Tubelet+Sync})
-
\mathrm{TPR}(\mathrm{Tubelet-only})。
\]

\[
\Delta_{\mathrm{traj}}
=
\mathrm{TPR}(\mathrm{Full})
-
\mathrm{TPR}(\mathrm{Tubelet+Sync})。
\]

#### 5. 对比基线

应至少包括：

1. frame-wise PRC baseline；
2. image watermark transferred to video；
3. latent video watermark baseline；
4. decoder watermark baseline；
5. 公开 video diffusion watermark 方法或其近似复现版本。

#### 6. 预期结果

最终论文希望证明：

1. tubelet-level code 优于 frame-wise code；
2. temporal synchronization 显著提升 temporal crop、frame dropping 与 local clip detection；
3. trajectory statistic 提供独立补充证据；
4. Full 方法在 fixed low-FPR 下保持较高 attacked positive TPR；
5. attacked negative FPR 不失控；
6. 质量与时序一致性损失可控。

---

## 六、预期论文贡献表述

如果实验成立，本文贡献可以表述为：

1. 本文提出 temporal-synchronized tubelet code，将视频水印承载单元从逐帧 latent 扩展为跨帧 latent tubelet，并通过同步码显式恢复未知时间对齐关系。

2. 本文提出 Flow Matching trajectory statistic，将水印证据从静态 latent 投影扩展到采样轨迹速度场投影，使水印检测与 Flow Matching 生成机制绑定。

3. 本文提出 fixed low-FPR calibrated multi-evidence detector，在 clean negative 与 attacked negative 上统一标定阈值，并在 watermarked positive 与 attacked positive 上验证检测性能。

4. 本文通过系统消融证明 tubelet evidence、synchronization evidence 与 trajectory evidence 分别对应不同攻击失效模式，并对最终鲁棒性具有独立贡献。

5. 本文构建面向视频生成水印的完整评估协议，覆盖时间攻击、空间攻击、压缩攻击、局部片段检测、质量指标与运行开销。

---

## 七、与现有方法的差异定位

### （一）与图像水印逐帧迁移方法的差异

图像水印逐帧迁移方法将每帧视为独立图像，无法显式解决 temporal crop、frame dropping 与 local clip detection 中的时间索引错位问题。本文将水印定义在 latent tubelet 与 temporal synchronization 上，核心对象是时空结构，而不是单帧图像。

### （二）与 decoder watermark 方法的差异

Decoder watermark 通常通过修改 decoder 或训练 watermark decoder 来实现嵌入与提取。本文不以 decoder fine-tuning 作为主要贡献，而是直接在 DiT / Flow Matching 的 latent tubelet 与 trajectory statistic 上定义水印证据。

### （三）与普通 video latent watermark 的差异

普通 video latent watermark 主要关注在 latent 中嵌入可恢复消息。本文进一步将水印码与 temporal synchronization 和 Flow Matching trajectory statistic 绑定，目标是解决时间攻击和生成过程证据不足问题。

### （四）与 in-generation video watermark 的差异

已有 in-generation video watermark 可能通过初始噪声、VAE inversion 或模型内部扰动实现盲提取。本文的差异在于提出 temporal-synchronized tubelet trajectory code，并以 fixed low-FPR protocol 验证三个 evidence 的独立贡献。

---

## 八、为什么该方法不是工程拼接

本文需要在方法论上明确回答“为什么不是工程拼接”。关键论点如下。

### （一）统一编码对象

三个 evidence 并非来自无关模块，而是共享同一个 joint tubelet code：

\[
c_g=c^{\mathrm{pay}}_g\cdot c^{\mathrm{sync}}_\tau。
\]

tubelet evidence、sync evidence 与 trajectory evidence 都围绕 \(c_g\) 展开，因此它们属于同一结构化编码系统的不同观测投影。

### （二）统一攻击模型

三个 evidence 分别对应不同攻击失效模式：

1. tubelet evidence 解决 frame-wise evidence 在跨帧扰动下不稳定的问题；
2. synchronization evidence 解决 temporal desynchronization；
3. trajectory evidence 解决最终 latent / pixel evidence 被攻击削弱后缺少生成过程证据的问题。

### （三）统一统计判决

最终检测不是任意模块投票，而是在同一 \(H_0/H_1\) 假设检验下的 low-FPR calibrated detector：

\[
S_{\mathrm{final}}\ge \eta_\alpha。
\]

阈值由 calibration negative 固定，test 阶段不允许调参。

### （四）统一消融验证

每个 evidence 必须在相同协议下证明边际贡献。若某个 evidence 没有边际贡献，则不能作为核心贡献写入论文主张。

---

## 九、需要重点探索和验证的问题

### （一）Tubelet code 相关

1. 最优 \(L_t\) 是多少；
2. tubelet 空间尺寸是否应固定；
3. 是否需要 motion-aware carrier selection；
4. embedding margin \(\alpha\) 如何影响质量与检测；
5. latent projection 是否引入可检测分布偏移。

### （二）Temporal synchronization 相关

1. sync code 应采用何种序列；
2. offset search 与 scale search 的搜索空间多大；
3. search space 扩大会如何影响 attacked negative FPR；
4. local clip 多短时仍能检测；
5. frame dropping 非均匀时是否需要 dynamic time warping-like alignment。

### （三）Trajectory statistic 相关

1. inversion 是否稳定；
2. trajectory score 是否与 tubelet score 冗余；
3. velocity projection、displacement projection、curvature residual 哪个更有效；
4. trajectory evidence 对 compression、blur、temporal crop 哪类攻击更有贡献；
5. trajectory detection 的 runtime overhead 是否可接受。

### （四）Sampling-time embedding 相关

1. 是否需要修改 velocity field；
2. \(\lambda(t)\) 的最优时间窗口；
3. 约束是否破坏 motion consistency；
4. 是否会导致文本语义偏移；
5. 是否可以只作为 detector evidence，而不作为 embedding constraint。

### （五）统计协议相关

1. target FPR 取值是否足够严格；
2. calibration negative 数量是否足够支持低 FPR；
3. attacked negative 是否覆盖全部攻击；
4. ablation 是否需要各自独立阈值；
5. 多重搜索是否需要显式校正或完全交由 calibration negative 吸收。

---

## 十、预期阶段性产物

### （一）阶段 1 产物

1. `main_tpr_fpr_table.csv`；
2. `ablation_table.csv`；
3. `local_clip_curve.csv`；
4. `tubelet_length_ablation.csv`；
5. `sync_peak_examples.png`；
6. `method_validation_report_v1.md`。

### （二）阶段 2 产物

1. `real_video_attack_breakdown.csv`；
2. `quality_table.csv`；
3. `temporal_consistency_table.csv`；
4. `failure_case_gallery/`；
5. `vae_latent_probe_report.md`。

### （三）阶段 3 产物

1. `trajectory_score_distribution.png`；
2. `score_correlation_matrix.csv`；
3. `trajectory_ablation_table.csv`；
4. `runtime_breakdown.csv`；
5. `trajectory_probe_report.md`。

### （四）阶段 4 产物

1. `lambda_schedule_ablation.csv`；
2. `trajectory_aware_embedding_table.csv`；
3. `quality_robustness_tradeoff.png`；
4. `motion_artifact_failure_cases/`；
5. `flow_matching_probe_report.md`。

### （五）阶段 5 产物

1. 论文主表；
2. 论文消融表；
3. 攻击曲线；
4. 局部片段检测曲线；
5. 质量表；
6. runtime 表；
7. 附录统计协议；
8. 失败样例分析；
9. 完整方法机制图。

---

## 十一、导师讨论时应重点确认的问题

1. 是否认可将第一阶段定位为 synthetic video latent proxy，而非直接接入完整视频生成模型；
2. 是否认可 temporal-synchronized tubelet code 作为主算法原语；
3. 是否将 Flow Matching trajectory statistic 作为强主张，还是先作为探索性增量；
4. 是否采用 fixed low-FPR protocol 作为整个项目的评估主线；
5. 是否优先追求 CVPR / ICCV / ECCV / NeurIPS / ICLR，还是先以 ACM MM / TIFS / TDSC 风格形成完整系统论文；
6. 是否接受 trajectory-aware embedding 可能失败，并在必要时将主线收敛到 tubelet synchronization；
7. 是否需要引入真实开源 video diffusion watermark baselines，还是先做可复现近似基线；
8. 是否需要从第一阶段开始建立严格 records、threshold、split 与 manifest 机制。

---

## 十二、最终判断

本项目具备形成顶会级论文方法的潜力，但前提是不能将方法写成“多个 evidence 分支的工程融合”。正确的论文方法基础应为：

\[
\text{temporal-synchronized tubelet code}
+
\text{Flow Matching trajectory statistic}
+
\text{fixed low-FPR calibrated detector}。
\]

其中，temporal-synchronized tubelet code 是最稳健、最应优先验证的核心；Flow Matching trajectory statistic 是最具新颖性但风险最高的增量；fixed low-FPR protocol 是保证论文可信度和防止审稿质疑的基础。

因此，项目应从 `video_tubelet_sync_probe_v1` 开始，先证明 tubelet synchronization 在受控 latent 条件下成立，再逐步进入真实视频 VAE latent、trajectory statistic、DiT / Flow Matching sampling-time embedding 和完整论文协议。每个阶段只回答一个核心机制问题，并设置明确通过标准。只有这样，最终论文才有可能达到顶会投稿要求，并避免被质疑为工程拼接。
