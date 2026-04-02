#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const tasksPath = path.join(cwd, '.pipeline', 'tasks', 'tasks.json');
const briefPath = path.join(cwd, '.pipeline', 'docs', 'research_brief.json');
const mode = args.includes('--json') ? 'json' : 'table';
const filter = args.find(a => a.startsWith('--status='))?.split('=')[1] || null;
const nextOnly = args.includes('--next');

if (!fs.existsSync(tasksPath)) {
  console.error('No pipeline found. Run /drclaw:setup first.');
  process.exit(1);
}

function normalize(status) {
  const s = String(status || '').trim().toLowerCase();
  if (s === 'completed' || s === 'complete') return 'done';
  if (s === 'in_progress' || s === 'inprogress') return 'in-progress';
  if (s === 'todo' || s === 'open' || !s) return 'pending';
  return s;
}

const tasksData = JSON.parse(fs.readFileSync(tasksPath, 'utf8'));
let tasks = Array.isArray(tasksData) ? tasksData : tasksData?.tasks || [];

if (filter) tasks = tasks.filter(t => normalize(t.status) === filter);

if (nextOnly) {
  const next = tasks.find(t => normalize(t.status) === 'pending');
  if (!next) { console.log('All tasks complete.'); process.exit(0); }
  if (mode === 'json') { console.log(JSON.stringify(next, null, 2)); }
  else { console.log(`Next: [${next.stage}] ${next.title} (id: ${next.id}, skill: ${next.skill || 'none'})`); }
  process.exit(0);
}

let projectName = 'Research Project';
try {
  if (fs.existsSync(briefPath)) {
    const brief = JSON.parse(fs.readFileSync(briefPath, 'utf8'));
    projectName = brief?.meta?.title || brief?.title || projectName;
  }
} catch {}

if (mode === 'json') {
  console.log(JSON.stringify({ project: projectName, tasks }, null, 2));
  process.exit(0);
}

const stages = ['Survey', 'Ideation', 'Experiment', 'Publication', 'Promotion'];
const stageStats = {};
let nextTask = null;

for (const task of tasks) {
  const stage = task.stage || 'Unknown';
  if (!stageStats[stage]) stageStats[stage] = { total: 0, done: 0, next: null };
  stageStats[stage].total++;
  if (normalize(task.status) === 'done') stageStats[stage].done++;
  if (!nextTask && normalize(task.status) === 'pending') {
    nextTask = task;
    if (!stageStats[stage].next) stageStats[stage].next = task.title;
  }
}

console.log(`\nPipeline Status: ${projectName}`);
console.log('\u2501'.repeat(56));
console.log('Stage          Tasks    Done     Next');
console.log('\u2500'.repeat(56));

for (const stage of stages) {
  const s = stageStats[stage] || { total: 0, done: 0, next: null };
  const done = s.total === 0 ? '\u2014' : s.done === s.total ? '\u2713' : `${s.done}/${s.total}`;
  const next = s.next || (s.done === s.total ? '\u2014' : '(blocked)');
  console.log(`${stage.padEnd(15)}${String(s.total).padEnd(9)}${done.padEnd(9)}${next}`);
}

console.log('\u2501'.repeat(56));
if (nextTask) {
  console.log(`\nNext: Run /drclaw:run to execute "${nextTask.title}"`);
}
