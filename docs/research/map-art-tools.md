# Map and Art Tooling Research (Internet-Sourced)

Date: 2026-02-24

## 1) Goal

Define a production-ready tooling stack for:

1. High-quality fantasy visuals (images, sprites, tokens, scene art).
2. Map creation/import for dungeon, room, village/city, and outdoor/world.
3. A polished result comparable in production quality to top tabletop products, while keeping art original and legally safe.

## 2) Recommended Integration Stack

## A) Runtime Map Format and Import Backbone

Primary recommendation:

1. `Tiled` JSON/TMX as internal editable map source of truth for runtime map layers and metadata.
2. `Universal VTT` (`.dd2vtt` / equivalent JSON payloads) as interoperability format for battlemap tools.
3. Import normalization service to convert all incoming map exports to the project's canonical schema.

Why:

1. Tiled has robust export automation (`--export-map`) and JSON format support.
2. Universal VTT is already used across common map tools and importer ecosystems.
3. This gives fast content onboarding while preserving engine-level consistency.

## B) Tool Picks by Map Type

Dungeon and room maps:

1. `Dungeondraft`
   - Strengths: fast dungeon/cave generation, built-in lighting, VTT-focused export workflow, no subscription.
   - Integration value: exports Universal VTT for walls/lights workflow.
2. `Dungeon Alchemist`
   - Strengths: rapid map layout and direct export with walls/lights/doors for VTT import flows.
   - Integration value: fast production of encounter-ready battlemaps.

Village/city maps:

1. `Watabou Procgen Arcana` (city/village generators)
   - Strengths: fast procedural generation; permissive usage statement for generated maps.
   - Integration value: ideal for generating many settlement variants quickly.
2. `Inkarnate`
   - Strengths: city/village support, high-resolution exports, large art library.
   - Integration value: high-polish handcrafted visual maps for showcase regions.

Outdoor/world maps:

1. `Azgaar Fantasy Map Generator`
   - Strengths: highly customizable world map generation and data-rich exports.
   - Integration value: world/region-scale generation and campaign geography scaffolding.
2. `Inkarnate`
   - Strengths: strong world/region map art and export quality.
   - Integration value: polished final map visuals for player-facing material.

## C) AI Art and Sprite Pipeline (Python)

Primary recommendation:

1. `Hugging Face Diffusers` as the default Python-native generation layer.
2. `Stable Diffusion` text-to-image and inpainting pipelines for assets and scene variants.
3. `ControlNet` conditioning to enforce composition/layout consistency.
4. `LoRA` adapters for controlled style specialization over time.
5. Optional local orchestration via `ComfyUI` server API for visual workflow graph control.

Optional compatibility layer:

1. `AUTOMATIC1111` API mode (`--api`) for teams already using A1111 tooling.

## 3) Integration Architecture

## A) Art Generation Service

Build a Python service with:

1. Job queue for batch generation.
2. Reproducibility metadata per output:
   - model/version
   - prompt and negative prompt hash
   - seed
   - pipeline/workflow version
   - control inputs
3. Asset QA stage:
   - automatic checks (resolution, alpha channel, readability, style tags)
   - human approval for release assets

## B) Map Import Service

Build adapters for:

1. Tiled JSON/TMX
2. Universal VTT exports
3. Dungeon Alchemist compatible JSON exports
4. Azgaar and Watabou outputs (JSON/SVG/PNG + metadata where available)

Normalization output:

1. Grid geometry
2. Layers and render hints
3. Walls/doors/lights
4. Regions/spawn points
5. Asset references

## C) Quality and Legal Controls

1. Add `Art Quality Gate` and `Asset Licensing Gate` in CI/release checks.
2. Keep an art provenance registry for all imported/generated assets.
3. Enforce original style direction; avoid copying protected brand characters, logos, or trademarked visual marks.

## 4) Best Practical First Cut (MVP)

1. Map imports:
   - Tiled JSON
   - Universal VTT imports
   - one settlement generator path (Watabou or Azgaar)
2. Art pipeline:
   - Diffusers txt2img + inpainting scripts
   - ControlNet for layout consistency
   - initial curated LoRA set only if style variance becomes blocking
3. Asset packs:
   - character portraits
   - creature tokens
   - item icons
   - scene backdrops

## 5) Source Links

1. Tiled export formats and automation:
   - https://doc.mapeditor.org/en/latest/manual/export/
   - https://doc.mapeditor.org/en/stable/reference/json-map-format/
   - https://doc.mapeditor.org/en/stable/manual/export-generic/
2. Dungeondraft official features and VTT integrations:
   - https://dungeondraft.net/
3. Dungeon Alchemist export support:
   - https://www.dungeonalchemist.com/
4. Universal VTT import ecosystem references:
   - https://foundryvtt.com/packages/dd-import/
   - https://www.dungeonfog.com/support/tutorials/foundryvtt/
   - https://www.dungeonfog.com/news/campaigns-update/
5. Inkarnate map types and export limits:
   - https://inkarnate.com/faq
6. Watabou generators and usage FAQ:
   - https://watabou.github.io/faq.html
7. Azgaar Fantasy Map Generator:
   - https://github.com/Azgaar/Fantasy-Map-Generator
8. Diffusers Stable Diffusion/ControlNet/Inpainting/LoRA docs:
   - https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/text2img
   - https://huggingface.co/docs/diffusers/en/api/pipelines/controlnet
   - https://huggingface.co/docs/diffusers/en/using-diffusers/inpaint
   - https://huggingface.co/docs/diffusers/api/loaders/lora
9. ComfyUI server routes:
   - https://docs.comfy.org/development/comfyui-server/comms_routes
10. AUTOMATIC1111 API mode:
   - https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API
11. Stability AI model overview:
   - https://stability.ai/stable-image
