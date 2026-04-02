#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const tasksPath = path.join(cwd, '.pipeline', 'tasks', 'tasks.json');
const briefPath = path.join(cwd, '.pipeline', 'docs', 'research_brief.json');

if (!fs.existsSync(tasksPath)) {
  process.exit(0);
}

try {
  const tasksData = JSON.parse(fs.readFileSync(tasksPath, 'utf8'));
  const tasks = Array.isArray(tasksData) ? tasksData : tasksData?.tasks || [];

  const stages = {};
  let nextTask = null;

  for (const task of tasks) {
    const stage = task.stage || 'Unknown';
    if (!stages[stage]) stages[stage] = { total: 0, done: 0 };
    stages[stage].total++;
    if (task.status === 'done' || task.status === 'completed') stages[stage].done++;
    if (!nextTask && (task.status === 'pending' || task.status === 'todo' || !task.status)) {
      nextTask = task;
    }
  }

  let projectName = 'Research Project';
  if (fs.existsSync(briefPath)) {
    try {
      const brief = JSON.parse(fs.readFileSync(briefPath, 'utf8'));
      projectName = brief?.meta?.title || brief?.title || projectName;
    } catch {}
  }

  const totalDone = Object.values(stages).reduce((s, v) => s + v.done, 0);
  const totalAll = Object.values(stages).reduce((s, v) => s + v.total, 0);

  console.log(`[Dr. Claw] Pipeline detected: "${projectName}" — ${totalDone}/${totalAll} tasks done.`);
  if (nextTask) {
    console.log(`[Dr. Claw] Next task: "${nextTask.title}" (stage: ${nextTask.stage}, skill: ${nextTask.skill || 'none'})`);
    console.log(`[Dr. Claw] Run /drclaw:status for full progress or /drclaw:run to execute next task.`);
  } else {
    console.log(`[Dr. Claw] All tasks complete!`);
  }
} catch (err) {
  console.error(`[Dr. Claw] Error reading pipeline: ${err.message}`);
  process.exit(1);
}
