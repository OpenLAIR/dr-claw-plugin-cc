#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const tasksPath = path.join(cwd, '.pipeline', 'tasks', 'tasks.json');

const taskId = args.find(a => a.startsWith('--task-id='))?.split('=')[1];
const newStatus = args.find(a => a.startsWith('--status='))?.split('=')[1] || 'done';
const stage = args.find(a => a.startsWith('--stage='))?.split('=')[1];

if (!taskId && !stage) {
  console.error('Usage: update-task.mjs --task-id=<id> --status=<status>');
  console.error('   or: update-task.mjs --stage=<Stage> --status=<status>');
  process.exit(1);
}

if (!fs.existsSync(tasksPath)) {
  console.error('No pipeline found.');
  process.exit(1);
}

const tasksData = JSON.parse(fs.readFileSync(tasksPath, 'utf8'));
const isArray = Array.isArray(tasksData);
const tasks = isArray ? tasksData : tasksData?.tasks || [];

let updated = 0;
for (const task of tasks) {
  if (taskId && task.id === taskId) {
    task.status = newStatus;
    updated++;
  } else if (stage && task.stage === stage && !taskId) {
    task.status = newStatus;
    updated++;
  }
}

if (updated === 0) {
  console.error(`No tasks matched (task-id=${taskId || 'none'}, stage=${stage || 'none'}).`);
  process.exit(1);
}

fs.writeFileSync(tasksPath, JSON.stringify(isArray ? tasks : { ...tasksData, tasks }, null, 2), 'utf8');
console.log(`Updated ${updated} task(s) to "${newStatus}".`);
