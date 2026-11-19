# PySide6 Desktop Application Best Practices (2026) for a Load-Test Studio GUI

## Threading model: QThread, QRunnable, signals/slots; running blocking work (Locust) off the UI thread

### Takeaway
Use QRunnable + QThreadPool for fire-and-forget background work, QThread for long-lived workers; communicate exclusively via signals/slots with QueuedConnection, and never touch widgets from worker threads. Cooperative cancellation via requestInterruption()/isInterruptionRequested() is the safe pattern.

### Cited Findings
- QRunnable is not a QObject, so it cannot emit signals directly; pair it with a QObject "signals" object to expose started/finished/error/result signals. — [PySide6 Blueprints ch.29](https://leanpub.com/read/pyside6blueprints/29-qthreadpool-and-qrunnable)
- Signals/slots are thread-safe across threads via queued connections, allowing safe GUI updates from worker threads. — [PythonGUIs multithreading tutorial](https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/)
- QThread.currentThread().objectName() and requestInterruption()/isInterruptionRequested() support cooperative cancellation and cleanup. — [Medium: Safe QThread Usage](https://medium.com/@asilichenko/safe-qthread-usage-in-pyside6-signals-cancellation-and-error-handling-bf1823d95354)
- Don't thread what you can't parallelize: prefer QProcess for subprocesses and async for IO; threads add complexity. — [co3dex: Qt async done right](https://www.co3dex.com/blog/threading-antipatterns-qt-async/)
- For Locust: run the runner in a QThread/QRunnable, emit metrics via signals at throttled intervals, call requestInterruption on stop; avoid blocking the GUI event loop. — [penguintutor QThreadPool guide](https://penguintutor.com/programming/pyside6-qthreadpool)

### Inferences
- A Locust load run is long-lived and needs cancellation + streaming metrics, so a QThread subclass with signals is a better fit than QRunnable.

### Gaps
- No measured guidance on signal emission rate limits for high-frequency metric streams (e.g., 100+ RPS updates); recommend throttling in the worker.

## Charting: pyqtgraph vs matplotlib for real-time metrics

### Takeaway
Use pyqtgraph for live load-test metrics (60 fps, <10 ms latency, OpenGL); reserve matplotlib for static/publication-quality export only.

### Cited Findings
- pyqtgraph renders ~50-60 fps with <10 ms latency vs matplotlib ~5-15 fps / ~200 ms+ latency; OpenGL-accelerated. — [pyqtgraph.com comparison](https://pyqtgraph.com/is-pyqtgraph-better-than-matplotlib-for-live-plots)
- pyqtgraph is built on Qt/NumPy and handles millions of points efficiently; matplotlib is more mature for publication graphics. — [pyqtgraph docs intro](https://pyqtgraph.readthedocs.io/en/pyqtgraph-0.11.1/introduction.html)
- Live-plotting desktop apps are commonly built with PySide6 + pyqtgraph. — [Colorado physics labs guide](https://physicslabs.colorado.edu/courses/python/lab-software/building-a-gui)

### Inferences
- For a load studio, drive pyqtgraph plots from worker-thread signals updating PlotDataItem with appendData/setData; avoid recreating plots per update.

### Gaps
- None significant.

## Theming: QSS, dark/light switching, design tokens

### Takeaway
Use a token-driven QSS generator (e.g., qt-material or QDarkStyleSheet) with runtime palette swap; avoid hardcoding colors; consider KDAB's advice that QStyle subclasses beat QSS long-term.

### Cited Findings
- Qt-Material provides dark/light themes, custom accents, env-var tokens (QTMATERIAL_PRIMARYCOLOR etc). — [qt-material GitHub](https://github.com/UN-GCPDS/qt-material)
- QDarkStyleSheet is the most complete dark/light stylesheet for Qt/PySide/PyQt. — [QDarkStyleSheet](https://github.com/ColinDuquesnoy/QDarkStyleSheet)
- qtshadcn resolves light/dark palettes from XML tokens and renders QSS via Jinja2. — [qtshadcn PyPI](https://pypi.org/project/qtshadcn/)
- Qt 6 observes OS dark/light changes; palette/QStyle updates propagate. — [Qt forum OS-independent colour scheme](https://forum.qt.io/topic/164164/os-independent-colour-scheme-with-pyside6)
- KDAB argues QStyle subclasses are cleaner than QSS for custom styling long-term. — [KDAB: Say No to Qt Style Sheets](https://www.kdab.com/say-no-to-qt-style-sheets/)
- pyqtdarktheme supports OS theme + accent sync for PySide/PyQt. — [pyqtdarktheme context7](https://context7.com/5yutan5/pyqtdarktheme)

### Inferences
- For a design-token approach: define semantic tokens (surface, text, accent) in Python dicts, generate QSS at runtime, apply via QApplication.setStyleSheet.

### Gaps
- No canonical token schema; libraries differ. Pick one and stay consistent.

## Packaging: PyInstaller, optional extras, cross-platform

### Takeaway
Use PyInstaller in --onedir mode with --noupx; prefer pyside6-deploy or Nuitka for smaller binaries; ship PySide6-Essentials to trim; test on each target OS.

### Cited Findings
- PyInstaller explicitly disallows collecting multiple Qt bindings; use --onedir and --noupx for PySide6. — [PyInstaller 6.22 changelog](https://pyinstaller.org/en/latest/CHANGES.html)
- Qt for Python provides pyside6-deploy for cross-platform deployment. — [Qt deployment docs](https://doc.qt.io/qtforpython-6/deployment/index.html)
- PySide6-Essentials trims to Core/Gui/Widgets (no Addons/WebEngine). — [pulsescribe BUILDING_WINDOWS](https://github.com/KLIEBHAN/pulsescribe/blob/master/docs/BUILDING_WINDOWS.md)
- Nuitka produces smaller executables as an alternative. — [Erriez pyside6-nuitka-deployment](https://github.com/Erriez/pyside6-nuitka-deployment)

### Inferences
- For optional extras (e.g., locust, pyqtgraph), use extras_require and conditional imports; PyInstaller hooks must collect submodules.

### Gaps
- No verified benchmark of PyInstaller vs Nuitka size/startup for this app; measure locally.

## Accessibility and responsiveness

### Takeaway
Set tab order explicitly, provide accessible names/roles via QAccessible, support keyboard-only navigation, and keep UI responsive by moving blocking work off the main thread.

### Cited Findings
- QAccessible provides enums/static functions for AT servers/clients (screen readers). — [Qt QAccessible docs](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QAccessible.html)
- Qt focus docs: tab order customizable; Shift+Tab reverses. — [Qt focus docs](https://doc.qt.io/qt-6/focus.html)
- cwidgets offers accessible custom widgets for PySide6/PyQt6. — [cwidgets GitHub](https://github.com/hedi-bettaieb/cwidgets)
- Playwright can drive headless UI tests for PySide6 apps. — [See-Reading-Order keyboard accessibility](https://github.com/Community-Access/See-Reading-Order/blob/main/README_KEYBOARD_ACCESSIBILITY.md)

### Inferences
- Combine setTabOrder, setAccessibleName/Description, and focus policies; test with screen reader + keyboard-only flows.

### Gaps
- MaestroLibrary studio code was not available locally; patterns could not be inspected. Recommend fetching that reference separately.