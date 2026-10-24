---
title: "Meta's Generative Ads Model (GEM): The Central Brain Accelerating Ads Recommendation AI Innovation"
source: https://engineering.fb.com/2025/11/10/ml-applications/metas-generative-ads-model-gem-the-central-brain-accelerating-ads-recommendation-ai-innovation/
author:
  - "[[Huayu Li]]"
  - "[[Xiaoyi Liu]]"
published: 2025-11-10
created: 2026-01-31
description: We're sharing details about Meta's Generative Ads Recommendation Model (GEM), a new foundation model that delivers increased ad performance and advertiser ROI by enhancing other ads recommendation …
tags:
  - clippings
status: Unread
note:
related:
---
GEM is Meta's largest foundation model for ads recommendation, trained across thousands of GPUs with an LLM-inspired architecture. ==Since launch it has increased ad conversions 5% on Instagram and 3% on Facebook Feed in Q2.==

Three pieces make it work. A new architecture separates sequence features (user activity history) from non-sequence features (user and ad attributes) and is about four times more efficient than earlier ranking models. Post-training transfer pushes GEM's knowledge into hundreds of smaller vertical models through distillation, roughly twice as effective as standard distillation. ==A rebuilt training stack delivers a 23x increase in effective training FLOPs on 16x more GPUs.==

Next, Meta plans to train GEM across text, image, audio, and video, and move toward a single model ranking both organic content and ads.
