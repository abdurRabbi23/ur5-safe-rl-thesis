# সারাংশ (বাংলা) — অ্যালগরিদম অডিট ও ট্রেনিং প্যারামিটার

লেখা: ২০২৬-০৭-৩১ (Day 23)। মূল ইংরেজি ডকুমেন্ট: `ALGORITHM_AUDIT.md` (এই ফোল্ডারে)।

---

## ১. কী পাওয়া গেছে এবং কী করা হয়েছে — সংক্ষেপে

তুমি যা লক্ষ্য করেছিলে সেটা সঠিক ছিল: শুরুর দিকে PPO ভালো করত, এখন cPPO সবসময় জিতছে এবং
১০০% goal-reach দেখাচ্ছে — এটা সন্দেহজনক লেগেছিল। অডিট করে দেখা গেল, তুমি ঠিকই ধরেছিলে।

### মূল সমস্যা: constraint (λ) কার্যত বন্ধ ছিল, তবুও cPPO জিতছিল

cPPO-এর তিনটা সিড রানেই `cost_lambda` (λ, Lagrange multiplier) প্রায় পুরো ট্রেনিং জুড়ে
**০.০** ছিল। `cppo_s2` নামের রানে তো λ **একবারও** ০ থেকে সরেনি। গণিতের দিক থেকে, λ=০ হলে
PPO-Lagrangian-এর আপডেট আর সাধারণ PPO-এর আপডেট **হুবহু একই** — কারণ combined advantage
`(A_reward − λ·A_cost)/(1+λ)` তখন শুধু `A_reward`-এ পরিণত হয়। অর্থাৎ constraint কিছুই করছিল
না, তাও cPPO প্রতিটা সিডে reward এবং safety দুটোতেই PPO-কে হারিয়ে দিচ্ছিল। এটা সম্ভব নয়
যদি না কোনো অ্যালগরিদম-বহির্ভূত পার্থক্য কোডে লুকিয়ে থাকে।

### আসল কারণ (root cause): একটাই গ্লোবাল gradient clipping

মূল rsl_rl-এর PPO কোড থেকে একটা লাইন সরাসরি কপি হয়ে গিয়েছিল:
`clip_grad_norm_(policy.parameters(), max_grad_norm)`। PPO-তে এই parameters হলো শুধু
actor + reward critic। কিন্তু cPPO-তে এর সাথে **cost critic**-ও যুক্ত ছিল (কারণ cPPO-এর
নিজস্ব একটা আলাদা cost-value নেটওয়ার্ক আছে)। `clip_grad_norm_` ফাংশনটা সব gradient-কে
**একসাথে একটা মাত্র সংখ্যা** দিয়ে স্কেল করে — তাই cost critic-এর gradient বড় হলে সেটা
actor-এর gradient-কেও ছোট করে ফেলত। ফলে cPPO আসলে PPO-ই ছিল, শুধু প্রতিটা আপডেটে একটু
ছোট, শান্ত পদক্ষেপ (step size) নিয়ে চলছিল — যেটা এলোমেলো reward landscape-এ কম ঝুঁকিতে
পড়ে এবং বেশি স্থিতিশীলভাবে converge করে। এটাকেই ভুল করে "constraint নিরাপত্তা ও reward
দুটোই বাড়িয়ে দিচ্ছে" বলে মনে হয়েছিল।

### আরও তিনটা সমস্যা পাওয়া গেছে

- **cost_limit (বাজেট) কখনো বাইন্ড করেনি**: বাজেট ধরা হয়েছিল ২৫, কিন্তু converge করা
  policy-র স্বাভাবিক cost ছিল মাত্র ৭–২৯। মানে বাজেট এমনিতেই যথেষ্ট ঢিলা ছিল, তাই লাগ্রাঞ্জিয়ান
  কখনো সক্রিয় হওয়ার দরকারই পড়েনি।
- **Jc (গড় episodic cost) হিসাব হচ্ছিল মাত্র ১০০টা এপিসোড দিয়ে**, অথচ প্রতি ব্যাচে ৪০৯৬টা
  এনভায়রনমেন্ট একসাথে শেষ হয় — মানে মাত্র ২.৪% ডেটা দিয়ে একটা গুরুত্বপূর্ণ সংখ্যা হিসাব
  হচ্ছিল, যেটা অস্থির (noisy) হওয়ারই কথা।
- **SAC ইভ্যালুয়েশনে র‍্যান্ডম action ব্যবহার হয়ে যেত** (একটা কোড-লজিক বাগ, এখনো রান করার
  আগেই ধরা পড়েছে) — এটা ঠিক করা হয়েছে যাতে SAC-এর ফলাফল ভুলভাবে "ব্যর্থ" না দেখায়।

### ১০০%/০% গোল-রিচ কি চিটিং? না।

cube যখন গ্রিপারের কাছে আসে, একটা "proximity weld" যান্ত্রিকভাবে cube-কে গ্রিপারের সাথে
আটকে দেয় (বাস্তব ফিজিক্যাল গ্রাসপিং নয়, একটা সরলীকরণ)। এর মানে cube-এর অবস্থান = TCP
(গ্রিপার-টিপ)-এর অবস্থান। তাই "goal-এর ১ সেমি-এর মধ্যে cube আছে কিনা" প্রশ্নটা আসলে
"policy কি reach করতে শিখেছে কিনা" প্রশ্নে পরিণত হয় — যেটা শিখে গেলে প্রায় প্রতিবারই
সফল হয়, না শিখলে প্রায় কখনোই না। তাই ১০০% বা ০% — এই দুই প্রান্তেই সংখ্যাটা আটকে যাওয়া
স্বাভাবিক একটা measurement-সীমাবদ্ধতা, কোনো কারচুপি নয়।

### কী কী ঠিক/তৈরি করা হয়েছে

- **কোড ফিক্স**: gradient clipping এখন দুই ভাগে হয় (actor+reward-critic আলাদা, cost-critic
  আলাদা), Jc-এর জন্য বাফার সাইজ বাড়িয়ে ৪০৯৬ করা হয়েছে, SAC eval-এ random-action গার্ড
  বসানো হয়েছে।
- **নতুন control arm (`ctrl`)**: এতে cost critic থাকবে কিন্তু λ জোর করে ০-তেই আটকে রাখা
  হবে (`lambda_max=0`)। এটা দিয়ে বোঝা যাবে ফিক্সটা আসলে কাজ করেছে কিনা — `ctrl` আর `ppo`
  প্রায় একই রকম আসা উচিত।
- **নতুন cost_limit=10 arm (`cppo10`)**: যাতে constraint সত্যিই সক্রিয় হয়।
- **SAC-এর জন্য নতুন config লেখা হয়েছে** (আগে ছিলই না)।
- **৫টা arm × ৫টা seed = ২৫টা ট্রেনিং রান** এবং তার eval-এর জন্য নতুন স্ক্রিপ্ট, একটা
  ২-সেকেন্ডের রিগ্রেশন টেস্ট (যেটা প্রমাণ করে ফিক্সটা গাণিতিকভাবে ঠিক), একটা ধাপে-ধাপে
  checklist (`RUN_CHECKLIST_v2.md`), এবং লগবুক/run_log আপডেট।
- পুরনো রেজাল্ট ফাইলগুলো মুছে ফেলা হয়নি, বরং উপরে "SUPERSEDED — quote করা যাবে না" লেখা
  বসানো হয়েছে — কারণ থিসিসে "একটা বড় ফলাফল আসলে একটা bug ছিল, এবং কীভাবে ধরা হলো" এটা
  নিজেই একটা ভালো narrative।

**থিসিসের দাবি এখন থেকে হবে**: `cppo10` বনাম `ctrl`-এর পার্থক্য — শুধু এটাই constraint-এর
আসল প্রভাব বলে গণ্য হবে। `cppo` বনাম `ppo`-র পুরনো পার্থক্যকে ভাঙা যাবে এভাবে:
`(cppo − ppo) = (ctrl − ppo) + (cppo − ctrl)` — প্রথম অংশটা bug-এর প্রভাব, দ্বিতীয়টা
constraint-এর আসল প্রভাব।

---

## ২. এনভায়রনমেন্ট ও ট্রেনিং প্যারামিটার — বিস্তারিত

### ২.১ টাস্ক ও রোবট

| বিষয় | মান |
|---|---|
| Task ID | `Isaac-Lift-Cube-UR5e-v0` |
| রোবট | UR5e (৬-DOF আর্ম) + Robotiq 2f-85 গ্রিপার |
| গ্রাসপিং মেকানিজম | **Proximity weld** — বাস্তব কন্টাক্ট গ্রাসপিং না; গ্রিপার বন্ধ (close)
কমান্ড দিলে এবং cube গ্রিপারের কাছাকাছি (৬ সেমি-এর মধ্যে) থাকলে cube-টা গ্রিপারের সাথে
"আটকে" (latch) যায়, প্রতি স্টেপে তার position গ্রিপারের reach-frame-এ বসিয়ে দেওয়া হয় |
| Episode দৈর্ঘ্য | ৫.০ সেকেন্ড @ ৫০ Hz = ২৫০ কন্ট্রোল-স্টেপ |
| Action space | ৬টা আর্ম জয়েন্ট (position control, scale 0.5) + ১টা বাইনারি গ্রিপার action |
| num_envs | ৪০৯৬ (PPO/cPPO, on-policy) · ১২৮ (SAC, off-policy) |

### ২.২ Cube ও Goal

- Cube শুরু হয় নির্দিষ্ট একটা পজিশনে (টেবিলের ওপর)।
- প্রতি এপিসোডে একটা নতুন **goal pose** র‍্যান্ডমলি sample হয়:
  `pos_x ∈ (0.4, 0.6)`, `pos_y ∈ (−0.25, 0.25)`, `pos_z ∈ (0.25, 0.5)` মিটার।
- এই goal পুরো এপিসোড জুড়ে স্থির থাকে (resampling শুধু এপিসোডের শুরুতে)।

### ২.৩ Reward Terms (মূল IsaacLab Lift env থেকে)

| Reward term | Weight | ব্যাখ্যা |
|---|---|---|
| `reaching_object` | 1.0 | গ্রিপার cube-এর কাছে যাওয়ার জন্য পুরস্কার |
| `lifting_object` | 15.0 | cube টেবিল থেকে ৪ সেমি-এর বেশি উঠলে পুরস্কার |
| `object_goal_tracking` | 16.0 | cube goal-এর কাছাকাছি গেলে পুরস্কার |
| `object_goal_tracking_fine_grained` | 5.0 | goal-এর খুব কাছে গেলে সূক্ষ্ম পুরস্কার |
| `action_rate` | −1e-4 | হঠাৎ action পরিবর্তনের জন্য শাস্তি |
| `joint_vel` | −1e-4 | বেশি জয়েন্ট-ভেলোসিটির জন্য শাস্তি |

### ২.৪ Safety Cost ফাংশন (Layer-1 constraint) — `safe_rl/costs.py`

প্রতি স্টেপে তিনটা "soft" (মসৃণ, ধাপে-ধাপে বাড়ে) penalty টার্ম যোগ হয়ে একটা মোট cost হয়:

| Cost টার্ম | থ্রেশহোল্ড | ব্যাখ্যা |
|---|---|---|
| Collision keep-out | `z_floor = 0.0` মি | আর্মের যেকোনো মনিটর করা লিংক টেবিল-লেভেলের নিচে গেলে |
| Joint-limit margin | `joint_margin = 0.10` রেডিয়ান (~৫.৭°) | কোনো জয়েন্ট তার সীমার এই মার্জিনের মধ্যে ঢুকলে |
| Singularity floor | `manip_floor = 0.045` | Yoshikawa manipulability (w = √det(JJᵀ)) এই মানের নিচে নামলে — মানে আর্ম "singular" (dexterity হারানো) কনফিগারেশনে ঢুকছে |

- প্রতিটা টার্মের weight = ১.০ (`w_collision = w_joint = w_manip = 1.0`)।
- মোট cost = ওজন-যুক্ত তিনটা টার্মের যোগফল। এটাই `extras["cost"]`-এ পাঠানো হয় (শুধু cPPO
  এটা ব্যবহার করে; PPO cost হিসাব করে কিন্তু ব্যবহার করে না, শুধু লগ করে)।
- **Cost budget (`cost_limit`)** = ২৫ (episodic, undiscounted) — Day 9-এ calibrate করা।
  ⚠️ এই বাজেট natural cost (৭–২৯)-এর ওপরেই বসে আছে, তাই এটা কখনো বাইন্ড করেনি — এজন্যই
  নতুন `cost_limit = 10`-এর একটা arm (`cppo10`) যোগ করা হয়েছে, যাতে সত্যিকারের constraint
  সক্রিয় হয়।

### ২.৫ PPO (baseline) হাইপারপ্যারামিটার

| প্যারামিটার | মান |
|---|---|
| Actor/Critic hidden layers | [256, 128, 64], activation = ELU |
| num_steps_per_env | ২৪ |
| num_learning_epochs | ৫ |
| num_mini_batches | ৪ |
| clip_param (PPO clip ε) | ০.২ |
| entropy_coef | ০.০০৬ |
| learning_rate | ১e-৪ (adaptive, KL-ভিত্তিক, `desired_kl = 0.01`) |
| gamma (discount) | ০.৯৮ |
| lam (GAE λ) | ০.৯৫ |
| max_grad_norm | ১.০ |
| max_iterations | ১৫০০ |

### ২.৬ cPPO (PPO-Lagrangian) — PPO-এর সব প্যারামিটার + অতিরিক্ত

cPPO-তে PPO-এর সব হাইপারপ্যারামিটার অপরিবর্তিত থাকে (একই নেটওয়ার্ক সাইজ, একই লার্নিং
রেট ইত্যাদি), শুধু নিচের constraint-সংক্রান্ত যন্ত্রপাতি যোগ হয়:

| প্যারামিটার | মান | ব্যাখ্যা |
|---|---|---|
| `cost_limit` | ২৫.০ (নতুন arm-এ ১০.০) | episodic cost বাজেট |
| `lambda_lr` | ০.০৩৫ | Lagrange multiplier (λ) কত দ্রুত আপডেট হবে |
| `lambda_init` | ০.০ | λ শুরু হয় ০ থেকে |
| `lambda_max` | ১০০.০ (নতুন control arm-এ ০.০) | λ কত পর্যন্ত বাড়তে পারবে |
| `cost_value_loss_coef` | ১.০ | cost-critic-এর loss-এর ওজন |
| `gamma_cost`, `lam_cost` | ০.৯৮, ০.৯৫ | cost-এর জন্য আলাদা discount/GAE (reward-এর সাথে একই) |
| `cost_buffer_size` | ৪০৯৬ (আগে ছিল ১০০ — অডিটে ধরা পড়া বাগ) | Jc হিসাবের জন্য কয়টা এপিসোড মনে রাখা হবে |

**কীভাবে কাজ করে**:
- একটা আলাদা **cost critic** নেটওয়ার্ক থাকে (reward critic-এর মতোই architecture, কিন্তু
  আলাদা ওজন) যেটা ভবিষ্যতের cost অনুমান করে।
- **Combined advantage**: `A = (A_reward − λ·A_cost) / (1 + λ)` — policy আপডেট এই
  advantage দিয়ে হয়।
- **λ (Lagrange multiplier) আপডেট** প্রতি iteration-এ একবার:
  `λ ← clip(λ + lambda_lr × (Jc − cost_limit), 0, lambda_max)`
  যেখানে `Jc` হলো সাম্প্রতিক এপিসোডগুলোর গড় cost। মানে policy যদি বাজেটের বেশি cost করে,
  λ বাড়ে এবং constraint আরও কড়া হয়ে ওঠে।
- **Gradient clipping (অডিট-ফিক্স করা)**: আগে actor + reward-critic + cost-critic সব
  একসাথে ক্লিপ হতো (bug)। এখন actor+reward-critic একসাথে, আর cost-critic আলাদাভাবে ক্লিপ
  হয় — যাতে cost-critic-এর gradient কখনো actor-এর step-সাইজ প্রভাবিত করতে না পারে।

### ২.৭ নতুন Audit Arms (৫টা arm, ৫টা seed করে মোট ২৫টা রান)

| Arm | Entry point | PPO/cPPO থেকে পার্থক্য | উদ্দেশ্য |
|---|---|---|---|
| `ppo` | `rsl_rl_cfg_entry_point` | — | Baseline |
| `ctrl` | `rsl_rl_ctrl_cfg_entry_point` | `lambda_max = 0` | Control — cost critic থাকবে কিন্তু constraint বন্ধ। `ctrl` বনাম `ppo` = শুধু bug-এর প্রভাব মাপা |
| `cppo` | `rsl_rl_cppo_cfg_entry_point` | `cost_limit = 25` (Day-9 বাজেট) | পুরনো বাজেট, প্রত্যাশা: আবারও λ≈০ থাকবে |
| `cppo10` | `rsl_rl_cppo10_cfg_entry_point` | `cost_limit = 10` | সত্যিকারের constraint সক্রিয় হওয়ার জন্য নতুন, কড়া বাজেট |
| `sac` | `skrl_sac_cfg_entry_point` | সম্পূর্ণ ভিন্ন অ্যালগরিদম (off-policy) | তৃতীয় অ্যালগরিদম হিসেবে তুলনা |

Seed সংখ্যা ৩ থেকে বাড়িয়ে **৫** করা হয়েছে, কারণ PPO-এর ফলাফল বাইমোডাল (কখনো পুরো ব্যর্থ,
কখনো পুরো সফল) — ৩টা seed দিয়ে এই বৈচিত্র্য পরিমাপ করা যায় না।

### ২.৮ SAC (নতুন, skrl-ভিত্তিক) প্যারামিটার

| প্যারামিটার | মান | ব্যাখ্যা |
|---|---|---|
| num_envs | ১২৮ (off-policy বলে কম লাগে) | ৪০৯৬ দিলে replay buffer দ্রুত ভরে যাবে |
| Network | [256, 128, 64], ELU (PPO-এর সাথে মিল রাখা হয়েছে) | ৫টা মডেল: policy, critic_1, critic_2, target_critic_1, target_critic_2 |
| discount_factor (γ) | ০.৯৮ | PPO-এর gamma-র সাথে মিলিয়ে |
| grad_norm_clip | ১.০ | PPO-এর max_grad_norm-এর সাথে মিলিয়ে |
| batch_size | ৪০৯৬ | প্রতি gradient step-এ কতগুলো sample |
| replay buffer | ৮০০০/env × ১২৮ env = ~১০ লাখ transition | |
| learning_starts / random_timesteps | ১০০০ | শুরুতে র‍্যান্ডম exploration |
| timesteps (মোট) | ৩৬০০০ (= PPO-এর ১৫০০ × ২৪) | |

⚠️ **তুলনার একটা গুরুত্বপূর্ণ সতর্কতা**: PPO/cPPO ১৫০০ iteration-এ মোট ~১৪৭.৫ মিলিয়ন
environment-step ব্যবহার করে (৪০৯৬ env-এর কারণে), কিন্তু SAC মাত্র ~৪.৬ মিলিয়ন step
ব্যবহার করে (১২৮ env)। তাই এদের তুলনা **environment-sample** অনুযায়ী ন্যায্য না, কিন্তু
**gradient-step** অনুযায়ী প্রায় সমান (দুটোতেই ~৩০-৩৫ হাজার gradient step)। থিসিসে বলে
দিতে হবে কোন মাপকাঠিতে তুলনা করা হচ্ছে।

### ২.৯ Evaluation প্রোটোকল

- **Eval seed**: ১০১, ১০২, ১০৩ (ট্রেনিং seed ১–৫ থেকে ইচ্ছাকৃতভাবে আলাদা)।
- প্রতি checkpoint × প্রতি eval-seed-এ ১০০০টা এপিসোড স্কোর করা হয় (মোট প্রতি arm-এ
  ৫ seed × ৩ eval-seed × ১০০০ = ১৫,০০০ এপিসোড)।
- Policy **deterministic** (exploration noise বন্ধ), observation corruption বন্ধ।
- মাপা হয় যা যা: goal-distance distribution (mean/median/p90/max), success @ ১/২/৫ সেমি,
  lift success (commanded goal height-এর ≥৫০%), singularity-crossing হার (w < 1e-4),
  episode-এর সর্বনিম্ন manipulability, episodic cost বনাম বাজেট।

---

সব বিস্তারিত টেকনিক্যাল ব্যাখ্যা ও প্রমাণ ইংরেজিতে আছে `ALGORITHM_AUDIT.md`-তে, এবং
ধাপে-ধাপে রান করার নির্দেশ আছে `RUN_CHECKLIST_v2.md`-তে।
