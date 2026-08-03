# Fonts for figure generation

`Comparison_test/results/scripts/make_final_results_figs.py` registers **every `.ttf` in this
folder** and uses Times New Roman if one of them provides it. If none does, it falls back to
Liberation Serif, prints a loud warning, and still produces every figure — a missing font never
blocks a build.

Filenames do not matter. The script reads the family name from inside each file, so Ubuntu's
`Times_New_Roman.ttf` and Windows' `times.ttf` both work with no renaming.

The script always prints one of these when it runs:

```
Times New Roman registered from 4 file(s) in Thesis_LaTeX/fonts/.
Font in use: Times New Roman
```

Check that line rather than guessing which typeface came out.

## Ubuntu 22.04 — the setup used for this thesis

```bash
sudo apt update
sudo apt install -y ttf-mscorefonts-installer
```

The installer shows a Microsoft EULA in a blue text dialog. Press **Tab** to highlight `<Ok>`,
press **Enter**, then **Tab** to `<Yes>` and **Enter** again. It then downloads the fonts from
SourceForge, so it needs a working connection.

Confirm it worked:

```bash
fc-list | grep -i "times new roman"
```

Then copy the four files into this folder:

```bash
mkdir -p ~/ur5-safe-rl-thesis/Thesis_LaTeX/fonts
cp /usr/share/fonts/truetype/msttcorefonts/Times_New_Roman*.ttf \
   ~/ur5-safe-rl-thesis/Thesis_LaTeX/fonts/
ls -la ~/ur5-safe-rl-thesis/Thesis_LaTeX/fonts/
```

Expect `Times_New_Roman.ttf`, `Times_New_Roman_Bold.ttf`, `Times_New_Roman_Italic.ttf` and
`Times_New_Roman_Bold_Italic.ttf`. Regular alone is enough for the current figures; the other
three are worth having in case a figure ever needs bold or italic.

### If the download step fails

SourceForge intermittently refuses the download, which leaves the package "installed" but with
no font files on disk. Retry with:

```bash
sudo apt install --reinstall -y ttf-mscorefonts-installer
```

If it still fails and this machine dual-boots Windows, the files can be copied straight off the
Windows partition instead (`Windows/Fonts/times*.ttf`).

## Other platforms

- **Windows** — `C:\Windows\Fonts`, files `times.ttf`, `timesbd.ttf`, `timesi.ttf`, `timesbi.ttf`.
  If Explorer collapses them into one grouped item, right-click and choose **Open**.
- **macOS** — `/Library/Fonts/` or `~/Library/Fonts/`.

## Why the files have to live in the repo

Figures are rendered by a Python script, not by LaTeX, and that script may run on the lab PC, on
the laptop, or in a sandbox. Installing the font system-wide only helps that one machine. Keeping
the `.ttf` files inside the repo is what makes the figures reproducible everywhere.

## Licensing — why this folder is gitignored

Times New Roman is a Monotype typeface. Using it to typeset a thesis is fine. Redistributing the
font files — which is what committing them to a public GitHub repository would do — is not
covered by the licence, and the same applies to files obtained through
`ttf-mscorefonts-installer`, whose EULA permits use but not redistribution.

`Thesis_LaTeX/fonts/*.ttf` is therefore listed in `.gitignore`. The files stay on local machines
and are installed per-machine with the commands above. This README **is** tracked, so anyone
cloning the repo can see what is missing and how to supply it.

## A licence-free alternative, if the EULA is unwanted

```bash
sudo apt install -y fonts-croscore
cp /usr/share/fonts/truetype/croscore/Tinos-*.ttf ~/ur5-safe-rl-thesis/Thesis_LaTeX/fonts/
```

Tinos is Apache-licensed and metrically identical to Times New Roman. It is freely
redistributable, so the `.gitignore` rule would not be needed for it. Note that this is the same
*class* of solution as the Liberation Serif fallback already in use — a metric clone rather than
Monotype's own font — so it is only worth doing if the EULA is the objection.

## Note on the thesis body text

The LaTeX book itself does not use these files. It uses `newtx` (falling back to `mathptmx`),
which are Times clones with identical metrics rather than Monotype's Times New Roman. A figure
rendered in true Times New Roman and body text set in newtx match in size and proportion but are
not byte-identical typefaces. This is normal and not worth fixing — the difference is invisible
at figure scale.
