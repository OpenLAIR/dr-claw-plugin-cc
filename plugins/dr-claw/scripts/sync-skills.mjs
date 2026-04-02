#!/usr/bin/env node
/**
 * Build-time script: copies all skills from the main dr-claw repo
 * into the plugin's skills/ directory.
 *
 * Usage: node sync-skills.mjs --source /path/to/vibelab-public/skills
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const args = process.argv.slice(2);
const srcIdx = args.indexOf('--source');
const sourceArg = srcIdx !== -1 ? args[srcIdx + 1] : args.find(a => a.startsWith('--source='))?.split('=')[1];

if (!sourceArg || !fs.existsSync(sourceArg)) {
  console.error('Usage: node sync-skills.mjs --source /path/to/vibelab/skills');
  process.exit(1);
}

const destDir = path.join(__dirname, '..', 'skills');

// Don't overwrite our plugin-specific skills or non-skill files
const SKIP = new Set([
  'INTEGRATION.md', 'README.md', 'skill-tag-mapping.json',
  'skills-catalog-v2.json', 'skills-taxonomy-v2.overrides.json',
  'skills-taxonomy-v2.schema.json', 'stage-skill-map.json',
  'drclaw-pipeline', 'drclaw-run',
  // Personal/machine-specific skills — do NOT sync into the plugin
  'lehigh-aisp-gpu', 'mac-mini-ssh', 'macbook-ssh', 'cross-machine-sync',
  'toggling-mac-displays', 'managing-1password', 'sending-lehigh-emails',
  'pose-interview-logging', 'pose-schedule', 'session-migrate',
  'searching-agent-sessions', 'managing-omnifocus-tasks', 'managing-calendar-events',
  'managing-uf-gpu', 'processing-forum-posts', 'searching-rednote-posts',
  'invoking-codex', 'invoking-gemini', 'managing-github-repos',
  'managing-obsidian-notes', 'managing-python-packages', 'managing-cli-wrapper-apis',
  'syncing-overleaf-papers', 'syncing-skill-hub', 'writing-standup-notes',
  'updating-leetcode-anki-cards', 'adding-leetcode-templates',
  'making-nsf-pose-insight-slides', 'making-skills',
  'batch-condensing-arxiv-papers', 'converting-pptx-to-images',
  'processing-gemini-talks', 'annotating-exhibit-pdfs',
  'obsidian-skills'
]);

const entries = fs.readdirSync(sourceArg, { withFileTypes: true });
let copied = 0;

for (const entry of entries) {
  if (!entry.isDirectory()) continue;
  if (SKIP.has(entry.name)) continue;

  const src = path.join(sourceArg, entry.name);
  const dest = path.join(destDir, entry.name);

  // Check that the skill has a SKILL.md (valid skill directory)
  const skillMdPath = path.join(src, 'SKILL.md');
  if (!fs.existsSync(skillMdPath)) {
    // Check subdirectories for SKILL.md (nested skill structure)
    const hasNestedSkill = fs.readdirSync(src, { withFileTypes: true }).some(e => {
      if (e.isDirectory()) {
        return fs.existsSync(path.join(src, e.name, 'SKILL.md'));
      }
      return false;
    });
    if (!hasNestedSkill) {
      // Still copy — some skill dirs use different structures
    }
  }

  fs.cpSync(src, dest, { recursive: true, force: true });
  copied++;
}

// Also copy config files into drclaw-pipeline/references/
const configFiles = ['stage-skill-map.json', 'skill-tag-mapping.json'];
for (const cf of configFiles) {
  const src = path.join(sourceArg, cf);
  const refDest = path.join(destDir, 'drclaw-pipeline', 'references', cf);
  if (fs.existsSync(src) && fs.existsSync(path.dirname(refDest))) {
    fs.copyFileSync(src, refDest);
  }
}

console.log(`Synced ${copied} skill directories to ${destDir}`);
