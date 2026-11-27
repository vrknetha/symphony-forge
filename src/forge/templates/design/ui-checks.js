// Shared by close and the canvas renderer. No package or model is needed.
async function check(files) {
  const fs = await import('node:fs');
  const path = await import('node:path');
  const { spawnSync } = await import('node:child_process');
  // Close sends JSON over stdin so its changed-file list has no command-line limit.
  // The canvas renderer can also pass a few file names as arguments.
  if (!files.length) files = JSON.parse(fs.readFileSync(0, 'utf8') || '[]');
  const slash = file => file.replaceAll('\\', '/');
  const tests = file => /(?:^|\/)(?:__tests__|tests?)\//.test(slash(file)) ||
    /\.(?:test|spec)\.[^/]+$/.test(file);
  // Shadcn copies are skipped by every rule except motion-all.
  const excluded = file => /(?:^|\/)components\/ui\//.test(slash(file)) || tests(file);
  files = [...new Set(files.filter(file => /\.(tsx|jsx|html|css|vue|svelte)$/i.test(file) &&
    !tests(file) && fs.existsSync(file)))];
  const problems = [];
  if (!files.length) return { problems };
  const comment = (file, text) => /\.html$/i.test(file) ? `<!-- ${text} -->` :
    /\.[jt]sx$/i.test(file) ? `{/* ${text} */}` : `/* ${text} */`;
  const line = (text, index) => text.slice(0, index).split('\n').length;
  for (const file of files) {
    const raw = fs.readFileSync(file, 'utf8');
    const comments = /\.(html|css)$/i.test(file) ? /\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->/g :
      /\/\*[\s\S]*?\*\/|<!--[\s\S]*?-->|^[ \t]*\/\/[^\n]*/gm;
    const waived = new Set();
    for (const match of raw.matchAll(comments)) {
      const body = match[0].trim().replace(/^(?:\/\*|<!--|\/\/)|(?:\*\/|-->)$/g, '').trim();
      const waiver = body.match(/^forge-ui-ignore\s+([\w-]+):\s*(\S[\s\S]*)$/);
      if (waiver) waived.add(waiver[1]);
    }
    const text = raw.replace(comments, match => match.replace(/[^\n]/g, ' '));
    const report = (rule, index, message) => {
      if (!waived.has(rule)) problems.push(`${slash(file)}:${line(text, index)} ${rule}: ${message}\n` +
        `  ${comment(file, `forge-ui-ignore ${rule}: <reason>`)}`);
    };
    // Only motion-all also reads a // at the end of a code line. A // after a colon (a URL) or
    // inside a quoted string is not a comment, and only the text after it is set aside.
    let motion = text;
    if (!/\.(html|css)$/i.test(file)) motion = text.replace(/(["'`])(?:\\.|(?!\1)[^\\\n])*\1|(?<!:)\/\/[^\n]*/g, match => {
      if (!match.startsWith('//')) return match;
      if (/^forge-ui-ignore\s+motion-all:\s*\S/.test(match.slice(2).trim())) waived.add('motion-all');
      return match.replace(/[^\n]/g, ' ');
    });
    for (const match of motion.matchAll(/\btransition-all\b|\btransition(?:-?[pP]roperty)?\s*:\s*['"`]?all(?![\w-])/g))
      report('motion-all', match.index, 'List the properties that change instead of animating all of them.');
    if (excluded(file)) continue;
    const spacing = /\b(?:p[xytrbl]?|m[xytrblse]?|gap(?:-[xy])?|space-[xy])-\[-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|r?em|[sld]?v[wh]|vmin|vmax|ch|ex|cm|mm|in|pt|pc|%)?\]/g;
    for (const match of text.matchAll(spacing)) report('spacing-scale', match.index, `Use the spacing scale instead of ${match[0]}.`);

    // The owner's design rules that code can see. They apply to app screens: files under apps/ or
    // libs/ that are not email templates. A saved design canvas (docs/design/) is not a screen.
    const screen = /^(?:apps|libs)\//.test(slash(file)) && !/mail/i.test(slash(file));
    const owner = (rule, pattern, message, keep = () => true) => {
      if (screen) for (const match of text.matchAll(pattern)) if (keep(match)) report(rule, match.index, message);
    };
    // Class names sit in class="…", className={…} or a cn(…)/clsx(…)/cva(…) call. Words in text do not.
    const classes = [...text.matchAll(/\bclass(?:Name)?\s*=\s*(?:"[^"]*"|'[^']*'|\{(?:[^{}]|\{[^{}]*\})*\})|\b(?:cn|clsx|cva|twMerge)\((?:[^()]|\([^()]*\))*\)/g)]
      .map(match => [match.index, match.index + match[0].length]);
    // A theme value (--name: #hex inside :root, .dark or @theme) is where a hex colour belongs.
    const theme = index => {
      const before = text.slice(0, index), open = before.lastIndexOf('{');
      const start = Math.max(before.lastIndexOf('}', open), before.lastIndexOf(';', open), before.lastIndexOf('{', open - 1));
      return open > before.lastIndexOf('}') && /^(?::root|\.dark|@theme(?: inline)?)$/.test(before.slice(start + 1, open).trim());
    };
    const ms = (number, unit) => parseFloat(number) * (unit === 's' ? 1000 : 1);
    const hex = '#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})\\b(?!-)';
    const heavy = weight => weight === undefined || /^bold/.test(weight) || +weight >= 600;
    owner('bold-text', /\bfont-(?:bold|semibold|extrabold|black)\b|\bfont-\[(\d+)\]|font-?[wW]eight\s*:\s*['"`]?(bold|bolder|\d+)\b/g,
      'Use regular or medium weight, never bold.', match => heavy(match[1] ?? match[2]));
    owner('all-caps', /\btext-?[tT]ransform\s*:\s*['"`]?uppercase\b|(?<![\w-])uppercase(?![\w-])/g,
      'Write in sentence case, never all caps.',
      match => match[0] !== 'uppercase' || classes.some(([from, to]) => match.index >= from && match.index < to));
    owner('bg-gradient', /\bbg-(?:gradient|linear|radial|conic)\b|\b(?:linear|radial|conic)-gradient\s*\(/g,
      'Use a flat colour from the theme, never a gradient.');
    // A colour value follows a colour or custom property (color: #fff, fill="#fff") or sits in a Tailwind
    // value (bg-[#fff]). A link such as href="#feed" or text such as "Order #1234" is not a colour.
    owner('raw-hex', new RegExp(`(--[\\w-]+|[\\w-]*(?:color|background|border|shadow|fill|stroke|outline)[\\w-]*)['"]?\\s*[:=]\\s*` +
      `[{'"\`]*[^;{}'"\`\\n]*?(?<![\\w&/#-]|url\\(['"]?)${hex}|-\\[[^\\]\\s]*${hex}`, 'gi'),
    'Use a semantic theme token, never a hex value.', match => !(match[1]?.startsWith('--') && theme(match.index)));
    // Only a duration counts, not a delay: in a transition or animation shorthand the first time of each
    // comma-separated item is its duration; every time in a duration property is one.
    owner('slow-motion', /\bduration-(\d+)\b|\bduration-\[(\d*\.?\d+)(ms|s)\]|\b(?:transition|animation)(-?[dD]uration)?\s*:\s*['"`]?([^;}\n'"`]*)|\.animate\s*\((?:[^()]|\([^()]*\))*?\bduration\s*:\s*(\d+)/g,
      'Keep motion under 300 ms.', match => {
        if (match[1]) return +match[1] >= 300;
        if (match[2]) return ms(match[2], match[3]) >= 300;
        if (match[6]) return +match[6] >= 300;
        const items = match[4] ? [match[5]] : match[5].replace(/\([^)]*\)/g, '').split(',');
        return items.some(item => [...item.matchAll(/(\d*\.?\d+)(ms|s)\b/g)].slice(0, match[4] ? Infinity : 1)
          .some(time => ms(time[1], time[2]) >= 300));
      });

    const html = /\.html$/i.test(file);
    const shell = html ? /<aside\b/i.exec(text) :
      /\.(tsx|jsx)$/i.test(file) ? /<SidebarProvider\b/.exec(text) : null;
    if (!shell) continue;
    let components = text;
    if (!html) {
      for (const imported of text.matchAll(/\bimport\s+[\s\S]*?\bfrom\s*['"](\.[^'"]+)['"]/g)) {
        const base = path.resolve(path.dirname(file), imported[1]);
        const candidate = [base, ...['.tsx', '.jsx', '.ts', '.js', '/index.tsx', '/index.jsx'].map(ext => base + ext)]
          .find(name => fs.existsSync(name) && fs.statSync(name).isFile());
        if (candidate && !excluded(candidate)) components += '\n' + fs.readFileSync(candidate, 'utf8')
          .replace(comments, match => match.replace(/[^\n]/g, ' '));
      }
    }
    const fold = html ? /<aside\b[^>]*\bdata-collapsible\s*=\s*['"]icon['"]/i.test(text) ||
      /<button\b[^>]*\baria-label\s*=\s*['"][^'"]*sidebar[^'"]*['"]/i.test(text) :
      /<Sidebar\b[^>]*\bcollapsible\s*=\s*(?:\{\s*)?['"]icon['"]/.test(components);
    if (!fold) report('shell-fold', shell.index, 'Let the sidebar fold to an icon rail.');
    if (!/<(?:CommandDialog|CommandInput)\b|<[\w:-]+\b[^>]*\b(?:type|role)\s*=\s*(?:\{\s*)?['"]search['"]/.test(components))
      report('shell-search', shell.index, 'Add a search control to the app shell.');
  }

  const windows = process.platform === 'win32';
  const name = windows ? 'impeccable.cmd' : 'impeccable';
  const launcher = [`.codex/skills/impeccable/scripts/${name}`, `.claude/skills/impeccable/scripts/${name}`,
    path.resolve(path.dirname(process.argv[1]), '../skills/impeccable/scripts', name)]
    .map(file => path.resolve(file)).find(file => fs.existsSync(file));
  const note = 'The design checker did not run. The other design checks still ran.';
  if (!launcher) return { problems, note };
  files = files.filter(file => !excluded(file));
  const allowed = new Set(files.map(file => path.resolve(file)));
  for (let offset = 0; offset < files.length; offset += 50) {
    const batch = files.slice(offset, offset + 50).map(file =>
      './' + slash(path.relative(process.cwd(), path.resolve(file))));
    let result;
    if (windows) {
      // Expand arguments from the environment once, with delayed expansion off.
      // This keeps spaces and shell characters in client file names literal.
      const env = { ...process.env, FORGE_UI_LAUNCHER: launcher };
      batch.forEach((file, i) => { env[`FORGE_UI_TARGET_${i}`] = file; });
      const args = batch.map((file, i) => `"%FORGE_UI_TARGET_${i}%"`).join(' ');
      result = spawnSync(process.env.ComSpec || 'cmd.exe', ['/d', '/v:off', '/s', '/c',
        `""%FORGE_UI_LAUNCHER%" detect --json --no-advisory ${args}"`],
      { encoding: 'utf8', env, windowsVerbatimArguments: true });
    } else result = spawnSync(launcher, ['detect', '--json', '--no-advisory', ...batch], { encoding: 'utf8' });
    if (result.status === 127 || result.error?.code === 'ENOENT') return { problems, note };
    if (result.error || ![0, 2].includes(result.status))
      throw new Error(`The design checker could not check ${batch.join(', ')}: ${result.error?.message || result.stderr}`);
    for (const finding of JSON.parse(result.stdout)) {
      if (!allowed.has(path.resolve(finding.file))) continue;
      const file = slash(path.relative(process.cwd(), finding.file));
      problems.push(`${file}:${finding.line || 1} ${finding.antipattern}: ${finding.description}\n` +
        `  ${comment(file, `impeccable-disable ${finding.antipattern} -- <reason>`)}`);
    }
  }
  return { problems: [...new Set(problems)] };
}

check(process.argv.slice(2)).then(result => process.stdout.write(JSON.stringify(result))).catch(error => {
  process.stderr.write(error.message + '\n');
  process.exitCode = 1;
});
