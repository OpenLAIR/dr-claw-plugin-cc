# Changelog

## 2026-02-06
- Initial version adapted from the Gemini skill `nanobanana-prompt-architect`.
- Revised to follow SOP: Academic Framework Figure Prompting (math-first, contrastive, layout-first).
- Integrated PaperBanana-inspired workflow (plan -> style -> critic) to reduce detail loss during style polishing.
- Removed hardcoded filesystem linking to external SOP file paths (skill is self-contained).
- Added decoupled SOP path lookup via filename search (Spotlight/find), and NeurIPS-style default aesthetic options.
