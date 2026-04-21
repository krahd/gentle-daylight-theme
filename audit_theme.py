#!/usr/bin/env python3
import json, os, re, sys, colorsys

def hex_from_value(val):
    if not isinstance(val, str):
        return None
    m = re.search(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", val)
    if m:
        h = m.group(0)
        if len(h) == 4:
            return '#' + ''.join([c*2 for c in h[1:]])
        return h.lower()
    # rgba(...) fallback (ignore alpha)
    m = re.search(r"rgba?\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", val)
    if m:
        r,g,b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return '#%02x%02x%02x' % (r,g,b)
    return None

def hex_to_rgb(hexstr):
    h = hexstr.lstrip('#')
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    r = int(h[0:2],16); g = int(h[2:4],16); b = int(h[4:6],16)
    return (r,g,b)

def srgb_linear(c):
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def luminance(hexstr):
    r,g,b = hex_to_rgb(hexstr)
    R = srgb_linear(r); G = srgb_linear(g); B = srgb_linear(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def contrast_ratio(a,b):
    L1 = luminance(a); L2 = luminance(b)
    hi = max(L1,L2); lo = min(L1,L2)
    return (hi + 0.05) / (lo + 0.05)

def adjust_lightness(hexstr, delta):
    r,g,b = hex_to_rgb(hexstr)
    rf, gf, bf = [x/255.0 for x in (r,g,b)]
    h,l,s = colorsys.rgb_to_hls(rf,gf,bf)
    l2 = max(0, min(1, l + delta))
    r2,g2,b2 = colorsys.hls_to_rgb(h,l2,s)
    return '#%02x%02x%02x' % (int(round(r2*255)), int(round(g2*255)), int(round(b2*255)))

def find_adjusted(base, against, target=3.0, max_steps=60):
    # try darken and lighten, return first successful candidate with minimal absolute change
    candidates = []
    for sign in ( -1, 1 ):  # darken first
        for i in range(1, max_steps+1):
            delta = sign * (i * 0.01)
            new = adjust_lightness(base, delta)
            c = contrast_ratio(new, against)
            if c >= target:
                candidates.append((abs(delta), new, delta, c))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0]

def main():
    theme_path = os.path.join(os.path.dirname(__file__), 'themes', 'github-light-custom-color-theme.json')
    if not os.path.exists(theme_path):
        print('Theme file not found:', theme_path)
        sys.exit(1)
    data = json.load(open(theme_path, encoding='utf-8'))
    colors = data.get('colors', {})

    important = [
        'editor.background', 'editor.foreground', 'sideBar.background', 'activityBar.background',
        'panel.background', 'terminal.background', 'tab.activeBackground', 'tab.inactiveBackground',
        'statusBar.background'
    ]

    resolved = {}
    for k in important:
        if k in colors:
            hv = hex_from_value(colors[k])
            if hv:
                resolved[k] = hv

    # fallback: if editor.foreground missing, we won't assume — we check black/white
    report_lines = []
    report_lines.append('Accessibility audit for theme: %s' % data.get('name', '(unnamed)'))
    report_lines.append('')

    report_lines.append('Summary of found UI colors:')
    for k,v in resolved.items():
        report_lines.append(' - %s: %s' % (k, v))
    report_lines.append('')

    report_lines.append('Contrast with black/white (WCAG):')
    for k,v in resolved.items():
        c_black = contrast_ratio(v, '#000000')
        c_white = contrast_ratio(v, '#ffffff')
        ok_black = c_black >= 4.5
        ok_white = c_white >= 4.5
        report_lines.append(' - %s: %s | black: %.2fx %s | white: %.2fx %s' % (
            k, v, c_black, '(AA)' if ok_black else '(fail)', c_white, '(AA)' if ok_white else '(fail)'
        ))
    report_lines.append('')

    eb = resolved.get('editor.background')
    if eb:
        report_lines.append('Contrast vs editor.background (%s):' % eb)
        for k in resolved:
            if k == 'editor.background':
                continue
            c = contrast_ratio(eb, resolved[k])
            report_lines.append(' - %s (%s): %.2fx %s' % (k, resolved[k], c, '(OK >=3)' if c>=3 else '(LOW <3)'))
        report_lines.append('')
    else:
        report_lines.append('No editor.background found; cannot compute pairwise UI contrasts.')
        report_lines.append('')

    report_lines.append('Issues and recommendations:')
    if 'editor.background' not in resolved:
        report_lines.append(' - Add `editor.background` to theme to anchor contrast checks.')
    else:
        eb = resolved['editor.background']
        c_black = contrast_ratio(eb, '#000000')
        c_white = contrast_ratio(eb, '#ffffff')
        if c_black >= 4.5:
            report_lines.append(' - `editor.foreground`: black (#000000) meets AA (%.2fx). Consider setting `editor.foreground` explicitly.' % c_black)
        elif c_white >= 4.5:
            report_lines.append(' - `editor.foreground`: white (#ffffff) meets AA (%.2fx). Consider setting `editor.foreground` explicitly.' % c_white)
        else:
            report_lines.append(' - `editor.foreground` neither black nor white meet 4.5:1 (black: %.2fx, white: %.2fx). Consider choosing a darker foreground (e.g. #111827) and set `editor.foreground` explicitly.' % (c_black, c_white))

    ui_targets = ['sideBar.background','panel.background','activityBar.background','terminal.background','tab.activeBackground']
    for key in ui_targets:
        if key in resolved and 'editor.background' in resolved:
            c = contrast_ratio(resolved['editor.background'], resolved[key])
            if c < 3.0:
                report_lines.append(' - Low separation: `%s` (%s) vs `editor.background` (%s) contrast %.2fx — recommend increasing separation to >=3:1.' % (key, resolved[key], resolved['editor.background'], c))
                adj = find_adjusted(resolved[key], resolved['editor.background'], target=3.0)
                if adj:
                    report_lines.append('    Suggested `%s`: %s (change %.2f, new contrast %.2fx)' % (key, adj[1], adj[2], adj[3]))
                else:
                    report_lines.append('    Could not compute a small lightness adjustment to reach 3:1 automatically; consider making `%s` noticeably darker or lighter.' % key)

    report_lines.append('')
    if not data.get('tokenColors'):
        report_lines.append('Token colors: none provided. Ensure your syntax/token colors have sufficient contrast against `editor.background`. Add `tokenColors` entries or `editor.foreground` to guarantee readable code tokens.')
    else:
        report_lines.append('Token colors: found %d entries — verify contrast for each token color against `editor.background`.' % len(data.get('tokenColors')))

    report_lines.append('\nAutomated checks done. Manual review recommended for:')
    report_lines.append(' - Tab text/icon legibility (active vs inactive).')
    report_lines.append(' - Activity Bar and Side Bar icon contrast and focus states.')
    report_lines.append(' - Terminal ANSI colors (if overridden) against `terminal.background`.')

    out = '\n'.join(report_lines)
    print(out)
    with open(os.path.join(os.path.dirname(__file__), 'accessibility-report.txt'), 'w', encoding='utf-8') as f:
        f.write(out)

if __name__ == '__main__':
    main()
