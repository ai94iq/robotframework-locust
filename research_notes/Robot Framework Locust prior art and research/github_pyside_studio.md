# GitHub PySide/Qt Desktop Applications as Test/Studio Tools

## Libraries with optional [gui]/[studio] extras using PySide6

### Takeaway
Optional PySide6 GUI extras are typically declared under `[project.optional-dependencies]` (PEP 621), with core library depending only on Python stdlib/numerics and GUI pulled in on demand; asammdf and superqt are canonical examples.

### Cited Findings
- asammdf documents PySide6 and pyqtgraph as optional dependencies for its GUI tool, installed separately from the core MDF reader — [asammdf docs](https://asammdf.readthedocs.io/en/latest/intro.html).
- superqt declares `pyside6`, `pyqt5`, `pyqt6` extras with version pins and OS-specific wheel constraints in pyproject.toml — [superqt pyproject](https://github.com/pyapp-kit/superqt/blob/main/pyproject.toml).
- p6-mcp exposes an optional `settings` extra pulling `PySide6-Essentials>=6.7` — [p6-mcp pyproject](https://raw.githubusercontent.com/nizarhamza/p6-mcp/main/pyproject.toml).
- dayu_widgets exposes `pyside2`/`pyside6` extras in setup.cfg — [dayu_widgets setup.cfg](https://github.com/phenom-films/dayu_widgets/blob/master/setup.cfg).
- gratinglab declares a `gui` extra combining PySide6-Essentials and matplotlib — [gratinglab pyproject](https://github.com/jamccoy/gratinglab/blob/master/pyproject.toml).
- fm_miraesee declares a `bundle` extra for pyinstaller rather than GUI — [fm_miraesee pyproject](https://raw.githubusercontent.com/chordinq/fm_miraesee/main/pyproject.toml).

### Inferences
- Pattern: keep core importable without Qt; guard GUI imports with try/except and raise a helpful ModuleNotFoundError pointing to the extra name.
- Pinning Qt versions per Python version (as superqt does for pyside6<6.12 on py<3.12) matters because Qt wheels have ABI quirks.

### Gaps
- No single canonical "studio" extra naming convention found; projects use gui/studio/settings/bundle inconsistently.

## PySide theming: dark/light switching, QSS, design tokens

### Takeaway
qt-material is the dominant ready-made theming layer for PySide6, offering XML theme files, runtime switching via QtStyleTools, and export to QSS/RCC for non-Python targets; QDarkStyleSheet remains the older dark/light stylesheet baseline.

### Cited Findings
- qt-material supports dark_* and light_* themes applied via `apply_stylesheet(app, theme='dark_teal.xml')`, with `invert_secondary=True` for light themes — [qt-material README](https://github.com/UN-GCPDS/qt-material/blob/master/README.md).
- Runtime theme change via `QtStyleTools` mixin and `add_menu_theme`/`show_dock_theme` helpers — [qt-material README](https://github.com/UN-GCPDS/qt-material/blob/master/README.md).
- Custom colors/design tokens defined in Android-style XML resource files (primaryColor, secondaryColor, etc.) — [qt-material README](https://github.com/UN-GCPDS/qt-material/blob/master/README.md).
- `export_theme` generates `.qss`, `.rcc`, and icon folder for use in C++ or other non-Python environments — [qt-material README](https://github.com/UN-GCPDS/qt-material/blob/master/README.md).
- QDarkStyleSheet described as "most complete dark/light style sheet for Qt applications" supporting PySide6/PyQt6 — [QDarkStyleSheet](https://github.com/ColinDuquesnoy/QDarkStyleSheet).
- Comel provides an opinionated light/dark toggler for PySide6 — [Comel](https://github.com/hueyyeng/Comel).

### Inferences
- Design tokens are typically color names in XML; QSS templates substitute env vars like QTMATERIAL_PRIMARYCOLOR.
- Runtime switching requires re-applying stylesheet to QApplication, not just a widget.

### Gaps
- No evidence of a token-based design system (spacing/typography tokens) beyond colors in these libraries.

## Real-time charting in PySide (pyqtgraph) for metrics dashboards

### Takeaway
pyqtgraph is the standard high-performance real-time plotting library for PySide6, achieving ~50-60 fps with <10 ms latency, versus matplotlib's 5-15 fps; PyQtLabGraph wraps it for polished live plotting.

### Cited Findings
- pyqtgraph built on PyQt/PySide and numpy, intended for mathematics/scientific/real-time use — [pyqtgraph.org](https://pyqtgraph.org).
- Benchmark: PyQtGraph ~50-60 fps, <10 ms latency vs matplotlib ~5-15 fps, ~200 ms+ — [pyqtgraph comparison](https://pyqtgraph.com/is-pyqtgraph-better-than-matplotlib-for-live-plots).
- asammdf uses pyqtgraph for GUI signal plotting with PySide6 — [asammdf](https://github.com/danielhrisca/asammdf).
- PyQtLabGraph is a polished live-plotting library for PySide6 based on PyQtGraph — [pyqtlabgraph](https://pypi.org/project/pyqtlabgraph).
- Resource-Monitor-On-Python uses PySide6 + pyqtgraph for real-time CPU/memory charts — [Resource-Monitor-On-Python](https://github.com/mk-samoilov/Resource-Monitor-On-Python).
- pyqtgraph requires pyopengl for 3D and SciPy for some procedures; Qt binding choice (PySide6/PyQt6) at import time — [pyqtgraph.org](https://pyqtgraph.org).

### Inferences
- For metrics dashboards, prefer pyqtgraph PlotWidget with rolling buffers; avoid matplotlib in live paths.
- PyInstaller packaging of pyqtgraph needs hidden imports for template modules (axisCtrlTemplate_*, plotConfigTemplate_*) as seen in asammdf.

### Gaps
- No concrete dashboard example with multi-panel metrics and theming found in search results.

## Packaging PySide apps (PyInstaller, wheels) and cross-platform

### Takeaway
Two main routes: PyInstaller with pyinstaller-hooks-contrib (Qt binding-aware hooks) and the official pyside6-deploy (Nuitka-based) wrapper; cross-compilation is not supported, build on target OS.

### Cited Findings
- pyside6-deploy wraps Nuitka and produces .exe/.app/.bin per platform for Windows/macOS/Linux — [pyside6-deploy docs](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html).
- pyside6-deploy builds on same OS as target; cross-compiling not supported — [the-final-study-ai-gui](https://github.com/alifazelidehkordi/the-final-study-ai-gui/blob/feature/cross-platform-gui/docs/GUI_SOURCE_INSTALL.md).
- PyInstaller disallows collecting multiple Qt bindings (PySide2/6, PyQt5/6) into one frozen app — [PyInstaller changelog](https://pyinstaller.org/en/stable/CHANGES.html).
- pyinstaller-hooks-contrib includes pyqtgraph hooks using Qt binding selection helper — [hooks commit](https://github.com/pyinstaller/pyinstaller-hooks-contrib/commit/2f8969639db645e24122e89fc2d08d7cc17a646b).
- PyInstaller on Linux pulls entire Qt package including unused WebEngine libs; macOS builds are smaller — [pyinstaller issue 6447](https://github.com/pyinstaller/pyinstaller/issues/6447).
- PySide6 wheels split into Essentials/Addons; optional webengine extra available — [PySide6 package details](https://doc.qt.io/qtforpython/package_details.html).
- asammdf includes pyinstaller hidden imports for pyqtgraph templates in plot.py — [asammdf plot.py](https://github.com/danielhrisca/asammdf/blob/18c71009ef8b4784a55a560675eec66911cb1419/asammdf/gui/widgets/plot.py).

### Inferences
- For a library with optional GUI, ship wheels without Qt; let extras pull PySide6; provide a separate deploy script for standalone app builds.
- Use pyinstaller-hooks-contrib rather than hand-written hooks; test on each target OS.

### Gaps
- No recent (2024-2026) comparison of pyside6-deploy vs PyInstaller reliability for large apps found.