# Gentle Daylight — A soft light theme designed to reduce eye strain

Gentle Daylight is a minimal light theme built from your `workbench.colorCustomizations` aimed at reducing eye strain while coding.

Install and package:

```bash
# (optional) install packaging tools
npm install -g yo generator-code @vscode/vsce

# package a VSIX for publishing
cd vscode-github-light-theme
npx -y @vscode/vsce package
```

To test locally, open the folder in VS Code and run the `Developer: Reload Window` command, or install the produced `.vsix` via `Extensions: Install from VSIX...`.
