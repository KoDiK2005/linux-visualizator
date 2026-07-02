const Desklet = imports.ui.desklet;
const Settings = imports.ui.settings;
const Mainloop = imports.mainloop;
const Lang = imports.lang;
const Clutter = imports.gi.Clutter;
const Cairo = imports.cairo;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const ByteArray = imports.byteArray;

// ---- тема (соответствует ui/widget/theme.py в Python-версии) ----
const COLOR_BG_TOP = [26 / 255, 27 / 255, 34 / 255];
const COLOR_BG_BOTTOM = [16 / 255, 17 / 255, 22 / 255];
const COLOR_BORDER = [1, 1, 1, 0.09];
const COLOR_TEXT = [230 / 255, 230 / 255, 235 / 255, 1];
const COLOR_LABEL = [150 / 255, 152 / 255, 160 / 255, 1];
const COLOR_CPU = [0x4f / 255, 0xc3 / 255, 0xf7 / 255, 1];
const COLOR_MEM = [0x81 / 255, 0xc7 / 255, 0x84 / 255, 1];
const COLOR_NET_DOWN = [0xff / 255, 0xb7 / 255, 0x4d / 255, 1];
const COLOR_NET_UP = COLOR_CPU;
const COLOR_DISK = [0xba / 255, 0x68 / 255, 0xc8 / 255, 1];
const COLOR_DISK_WRITE = [0xe5 / 255, 0x73 / 255, 0x73 / 255, 1];
const COLOR_WARN = [0xff / 255, 0xca / 255, 0x28 / 255, 1];
const COLOR_BAD = [0xef / 255, 0x53 / 255, 0x50 / 255, 1];

// ---- геометрия ----
const RING_SIZE = 36;
const RING_SPACING = 8;
const RING_THICKNESS = 4;
const BAR_HEIGHT = 12;
const BAR_SPACING = 5;
const SPARK_HEIGHT = 40;
const SPARK_LABEL_HEIGHT = 14;
const HISTORY_LEN = 60;
const HEADER_HEIGHT = 13;
const SECTION_SPACING = 14;
const MARGIN = 16;
const CORNER_RADIUS = 14;
const MIN_PARTITION_BYTES = 1 * 1024 * 1024 * 1024;
const DISK_DEVICE_RE = /^(sd[a-z]+|nvme\d+n\d+|mmcblk\d+|vd[a-z]+)$/;
const LABEL_FONT = 'Cantarell';
const NUMBER_FONT = 'Cantarell';
// Cairo toy-text API не делает автоматический fallback шрифта по глифу — Cantarell не
// содержит стрелки ↓/↑, поэтому для строк со стрелками нужен шрифт, где они точно есть.
const SYMBOL_FONT = 'DejaVu Sans';
const ANIMATION_INTERVAL_MS = 33; // ~30 fps, только на несколько кадров после каждого тика
const SMOOTHING_FACTOR = 0.25;

function readFile(path) {
    try {
        let [ok, contents] = GLib.file_get_contents(path);
        return ok ? ByteArray.toString(contents) : null;
    } catch (e) {
        return null;
    }
}

function lerp(a, b, t) {
    return a + (b - a) * t;
}

function lerpColor(c1, c2, t) {
    return [lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t), lerp(c1[3], c2[3], t)];
}

// Подмешивает жёлтый/красный к базовому цвету при высокой загрузке — быстрый визуальный сигнал.
function severityColor(baseColor, percent) {
    if (percent <= 70) return baseColor;
    if (percent <= 90) return lerpColor(baseColor, COLOR_WARN, (percent - 70) / 20);
    return lerpColor(COLOR_WARN, COLOR_BAD, Math.min(1, (percent - 90) / 10));
}

// ---- сглаживание значений между тиками, для плавной анимации (аналог ui/widget/animation.py) ----

function Smoother(initial) {
    this.value = initial || 0;
    this.target = this.value;
}
Smoother.prototype.setTarget = function (target) {
    this.target = target;
};
Smoother.prototype.step = function () {
    let delta = this.target - this.value;
    if (Math.abs(delta) < 0.05) {
        if (this.value !== this.target) {
            this.value = this.target;
            return true;
        }
        return false;
    }
    this.value += delta * SMOOTHING_FACTOR;
    return true;
};

function SmootherMap() {
    this._items = new Map();
}
SmootherMap.prototype.setTarget = function (key, target) {
    if (!this._items.has(key)) this._items.set(key, new Smoother(target));
    else this._items.get(key).setTarget(target);
};
SmootherMap.prototype.pruneExcept = function (keys) {
    let keep = new Set(keys);
    for (let key of Array.from(this._items.keys())) {
        if (!keep.has(key)) this._items.delete(key);
    }
};
SmootherMap.prototype.value = function (key) {
    let item = this._items.get(key);
    return item ? item.value : 0;
};
SmootherMap.prototype.step = function () {
    let changed = false;
    for (let item of this._items.values()) {
        if (item.step()) changed = true;
    }
    return changed;
};

// ---- сборщики метрик (аналог core/collectors/*.py, но через /proc напрямую) ----

function collectCpu(prevState) {
    let text = readFile('/proc/stat');
    if (!text) return { perCore: [], state: prevState };

    let newState = {};
    let perCore = [];
    for (let line of text.split('\n')) {
        if (!/^cpu\d/.test(line)) continue;
        let parts = line.trim().split(/\s+/);
        let name = parts[0];
        let fields = parts.slice(1, 8).map(Number);
        let idle = fields[3] + fields[4];
        let total = fields.reduce((a, b) => a + b, 0);
        newState[name] = { idle, total };

        let prev = prevState[name];
        let percent = 0;
        if (prev) {
            let deltaIdle = idle - prev.idle;
            let deltaTotal = total - prev.total;
            percent = deltaTotal > 0 ? 100 * (1 - deltaIdle / deltaTotal) : 0;
        }
        perCore.push(Math.max(0, Math.min(100, percent)));
    }
    return { perCore, state: newState };
}

// Средняя частота ядер в МГц из /proc/cpuinfo (Linux ядро публикует её без доп. привилегий,
// в отличие от cpufreq sysfs-файлов, которые не везде читаемы без root).
function collectCpuFrequencyMHz() {
    let text = readFile('/proc/cpuinfo');
    if (!text) return null;
    let matches = [...text.matchAll(/cpu MHz\s*:\s*([\d.]+)/g)];
    if (!matches.length) return null;
    let sum = matches.reduce((acc, m) => acc + parseFloat(m[1]), 0);
    return sum / matches.length;
}

// Ищет файл hwmon с температурой пакета CPU (Intel: "Package id 0", AMD: "Tctl"/"Tdie").
// Делается один раз при старте десклета и кэшируется — сам путь не меняется на лету.
function findCpuTempFile() {
    let labels = ['Package id 0', 'Tctl', 'Tdie'];
    for (let label of labels) {
        try {
            let argv = ['/bin/sh', '-c',
                "grep -s -l -d skip '" + label + "' /sys/class/hwmon/*/temp*_label 2>/dev/null | sed 's/_label/_input/' | head -n 1"];
            let proc = new Gio.Subprocess({ argv, flags: Gio.SubprocessFlags.STDOUT_PIPE });
            proc.init(null);
            let [, stdout] = proc.communicate_utf8(null, null);
            let path = stdout.trim();
            if (path) return path;
        } catch (e) {
            // пробуем следующую метку
        }
    }
    return null;
}

function collectCpuTemperatureC(tempFilePath) {
    if (!tempFilePath) return null;
    let text = readFile(tempFilePath);
    if (!text) return null;
    let millidegrees = parseInt(text.trim());
    return isNaN(millidegrees) ? null : millidegrees / 1000;
}

function collectMemory() {
    let text = readFile('/proc/meminfo');
    if (!text) return { percent: 0, swapPercent: 0 };

    let readField = (name) => {
        let m = text.match(new RegExp(name + ':\\s+(\\d+)'));
        return m ? parseInt(m[1]) * 1024 : 0;
    };
    let total = readField('MemTotal');
    let available = readField('MemAvailable');
    let swapTotal = readField('SwapTotal');
    let swapFree = readField('SwapFree');

    return {
        percent: total > 0 ? (100 * (total - available)) / total : 0,
        swapPercent: swapTotal > 0 ? (100 * (swapTotal - swapFree)) / swapTotal : 0,
    };
}

function collectNetwork(prevState, elapsedSec, interfaceFilter) {
    let text = readFile('/proc/net/dev');
    if (!text) return { recvRate: 0, sentRate: 0, state: prevState };

    let filter = (interfaceFilter || '').trim();
    let totalRx = 0;
    let totalTx = 0;
    for (let line of text.split('\n').slice(2)) {
        line = line.trim();
        if (!line) continue;
        let parts = line.split(/[:\s]+/);
        if (parts.length < 10) continue;
        if (parts[0] === 'lo') continue;
        if (filter && parts[0] !== filter) continue;
        totalRx += parseInt(parts[1]) || 0;
        totalTx += parseInt(parts[9]) || 0;
    }

    let recvRate = 0;
    let sentRate = 0;
    if (prevState && elapsedSec > 0) {
        recvRate = Math.max(0, (totalRx - prevState.rx) / elapsedSec);
        sentRate = Math.max(0, (totalTx - prevState.tx) / elapsedSec);
    }
    return { recvRate, sentRate, state: { rx: totalRx, tx: totalTx } };
}

function collectDiskUsage() {
    let argv = [
        '/bin/df', '-B1', '--output=target,size,pcent',
        '-x', 'tmpfs', '-x', 'devtmpfs', '-x', 'squashfs', '-x', 'overlay',
        '-x', 'proc', '-x', 'sysfs', '-x', 'cgroup', '-x', 'cgroup2',
        '-x', 'tracefs', '-x', 'debugfs', '-x', 'configfs', '-x', 'securityfs',
        '-x', 'pstore', '-x', 'mqueue', '-x', 'hugetlbfs', '-x', 'rpc_pipefs',
        '-x', 'fusectl', '-x', 'binfmt_misc',
    ];
    try {
        let proc = new Gio.Subprocess({ argv, flags: Gio.SubprocessFlags.STDOUT_PIPE });
        proc.init(null);
        let [, stdout] = proc.communicate_utf8(null, null);

        let partitions = [];
        for (let line of stdout.split('\n').slice(1)) {
            let parts = line.trim().split(/\s+/);
            if (parts.length < 3) continue;
            let size = parseInt(parts[1]);
            let percent = parseFloat(parts[2].replace('%', ''));
            if (isNaN(size) || size < MIN_PARTITION_BYTES || isNaN(percent)) continue;
            partitions.push({ mountpoint: parts[0], percent });
        }
        return partitions;
    } catch (e) {
        return [];
    }
}

function collectDiskIo(prevState, elapsedSec) {
    let text = readFile('/proc/diskstats');
    if (!text) return { readRate: 0, writeRate: 0, state: prevState };

    let totalReadSectors = 0;
    let totalWriteSectors = 0;
    for (let line of text.split('\n')) {
        let parts = line.trim().split(/\s+/);
        if (parts.length < 10) continue;
        if (!DISK_DEVICE_RE.test(parts[2])) continue;
        totalReadSectors += parseInt(parts[5]) || 0;
        totalWriteSectors += parseInt(parts[9]) || 0;
    }

    let readRate = 0;
    let writeRate = 0;
    if (prevState && elapsedSec > 0) {
        readRate = Math.max(0, ((totalReadSectors - prevState.read) * 512) / elapsedSec);
        writeRate = Math.max(0, ((totalWriteSectors - prevState.write) * 512) / elapsedSec);
    }
    return { readRate, writeRate, state: { read: totalReadSectors, write: totalWriteSectors } };
}

// ---- десклет ----

function LinuxVisualizatorDesklet(metadata, deskletId) {
    this._init(metadata, deskletId);
}

LinuxVisualizatorDesklet.prototype = {
    __proto__: Desklet.Desklet.prototype,

    _init: function (metadata, deskletId) {
        Desklet.Desklet.prototype._init.call(this, metadata, deskletId);

        this.settings = new Settings.DeskletSettings(this, metadata.uuid, deskletId);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'refresh-interval', 'refreshInterval', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'background-opacity', 'backgroundOpacity', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-cpu', 'showCpu', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'cpu-view', 'cpuView', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-cpu-freq', 'showCpuFreq', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-cpu-temp', 'showCpuTemp', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-mem', 'showMem', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-net', 'showNet', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'network-interface', 'networkInterface', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-disk', 'showDisk', this._onSettingsChanged);

        this._cpuState = {};
        this._netState = null;
        this._diskIoState = null;
        this._lastTickTime = null;
        this._cpuTempFile = findCpuTempFile();

        this._cpuPercents = [];
        this._cpuAverage = 0;
        this._cpuFreqMHz = null;
        this._cpuTempC = null;
        this._cpuHistory = [];
        this._memPercent = 0;
        this._swapPercent = 0;
        this._diskPartitions = [];
        this._netHistory = { recv: [], sent: [] };
        this._diskIoHistory = { read: [], write: [] };

        this._cpuSmoother = new SmootherMap();
        this._memSmoother = new Smoother();
        this._swapSmoother = new Smoother();
        this._diskSmoother = new SmootherMap();
        this._animationTimeoutId = null;

        this.window = new Clutter.Actor();
        this.setContent(this.window);

        this._tick();
    },

    on_desklet_removed: function () {
        if (this._timeoutId) Mainloop.source_remove(this._timeoutId);
        if (this._animationTimeoutId) Mainloop.source_remove(this._animationTimeoutId);
    },

    _onSettingsChanged: function () {
        if (this._timeoutId) {
            Mainloop.source_remove(this._timeoutId);
        }
        this._tick();
    },

    _tick: function () {
        let now = GLib.get_monotonic_time() / 1e6;
        let elapsed = this._lastTickTime ? now - this._lastTickTime : 0;

        if (this.showCpu) {
            let cpu = collectCpu(this._cpuState);
            this._cpuPercents = cpu.perCore;
            this._cpuState = cpu.state;
            this._cpuPercents.forEach((percent, idx) => this._cpuSmoother.setTarget(idx, percent));
            this._cpuSmoother.pruneExcept(this._cpuPercents.map((_, idx) => idx));

            this._cpuAverage = this._cpuPercents.length
                ? this._cpuPercents.reduce((a, b) => a + b, 0) / this._cpuPercents.length
                : 0;
            this._pushHistory(this._cpuHistory, this._cpuAverage);

            this._cpuFreqMHz = this.showCpuFreq ? collectCpuFrequencyMHz() : null;
            this._cpuTempC = this.showCpuTemp ? collectCpuTemperatureC(this._cpuTempFile) : null;
        }
        if (this.showMem) {
            let mem = collectMemory();
            this._memPercent = mem.percent;
            this._swapPercent = mem.swapPercent;
            this._memSmoother.setTarget(mem.percent);
            this._swapSmoother.setTarget(mem.swapPercent);
        }
        if (this.showNet) {
            let net = collectNetwork(this._netState, elapsed, this.networkInterface);
            this._netState = net.state;
            this._pushHistory(this._netHistory.recv, net.recvRate);
            this._pushHistory(this._netHistory.sent, net.sentRate);
        }
        if (this.showDisk) {
            this._diskPartitions = collectDiskUsage();
            this._diskPartitions.forEach((p) => this._diskSmoother.setTarget(p.mountpoint, p.percent));
            this._diskSmoother.pruneExcept(this._diskPartitions.map((p) => p.mountpoint));
            let io = collectDiskIo(this._diskIoState, elapsed);
            this._diskIoState = io.state;
            this._pushHistory(this._diskIoHistory.read, io.readRate);
            this._pushHistory(this._diskIoHistory.write, io.writeRate);
        }

        this._lastTickTime = now;
        this._render();
        this._startAnimation();

        let intervalMs = Math.max(200, this.refreshInterval || 1000);
        this._timeoutId = Mainloop.timeout_add(intervalMs, Lang.bind(this, this._tick));
    },

    // Плавно подкручивает кольца/полосы к новым значениям несколько кадров после каждого тика,
    // а не дёргает их скачком — так десклет выглядит живее без постоянной перерисовки.
    _startAnimation: function () {
        if (this._animationTimeoutId) return;
        this._animationTimeoutId = Mainloop.timeout_add(ANIMATION_INTERVAL_MS, Lang.bind(this, this._animateStep));
    },

    _animateStep: function () {
        let changed = false;
        if (this._cpuSmoother.step()) changed = true;
        if (this._memSmoother.step()) changed = true;
        if (this._swapSmoother.step()) changed = true;
        if (this._diskSmoother.step()) changed = true;

        if (changed) {
            this._render();
            return true;
        }
        this._animationTimeoutId = null;
        return false;
    },

    _pushHistory: function (array, value) {
        array.push(value);
        while (array.length > HISTORY_LEN) array.shift();
    },

    _render: function () {
        let width = 220;
        let y = MARGIN;
        let sections = [];

        if (this.showCpu && this._cpuPercents.length) {
            let view = this.cpuView || 'rings';
            let h;
            if (view === 'bars') {
                let count = this._cpuPercents.length;
                h = HEADER_HEIGHT + count * BAR_HEIGHT + (count - 1) * BAR_SPACING;
            } else if (view === 'graph') {
                h = HEADER_HEIGHT + SPARK_HEIGHT;
            } else {
                let ringsWidth = this._cpuPercents.length * (RING_SIZE + RING_SPACING) + RING_SPACING;
                width = Math.max(width, ringsWidth);
                h = HEADER_HEIGHT + RING_SIZE + 6;
            }

            let statParts = [Math.round(this._cpuAverage) + '%'];
            if (this.showCpuFreq && this._cpuFreqMHz) statParts.push((this._cpuFreqMHz / 1000).toFixed(1) + ' GHz');
            if (this.showCpuTemp && this._cpuTempC !== null) statParts.push(Math.round(this._cpuTempC) + '°C');

            sections.push({
                type: 'cpu', y, height: h, label: 'ПРОЦЕССОР', color: COLOR_CPU,
                view, statText: statParts.join('  '),
            });
            y += h + SECTION_SPACING;
        }
        if (this.showMem) {
            let h = HEADER_HEIGHT + BAR_HEIGHT * 2 + BAR_SPACING;
            sections.push({ type: 'mem', y, height: h, label: 'ПАМЯТЬ', color: COLOR_MEM });
            y += h + SECTION_SPACING;
        }
        if (this.showNet) {
            let h = HEADER_HEIGHT + SPARK_HEIGHT;
            sections.push({ type: 'net', y, height: h, label: 'СЕТЬ', color: COLOR_NET_DOWN });
            y += h + SECTION_SPACING;
        }
        if (this.showDisk) {
            let count = Math.max(this._diskPartitions.length, 1);
            let usageHeight = count * BAR_HEIGHT + (count - 1) * BAR_SPACING;
            let h = HEADER_HEIGHT + usageHeight + BAR_SPACING + SPARK_HEIGHT;
            sections.push({ type: 'disk', y, height: h, label: 'ДИСКИ', color: COLOR_DISK, usageHeight });
            y += h + SECTION_SPACING;
        }

        let totalWidth = width + MARGIN * 2;
        let totalHeight = sections.length ? y - SECTION_SPACING + MARGIN : MARGIN * 2;

        let canvas = new Clutter.Canvas();
        canvas.set_size(totalWidth, totalHeight);
        canvas.connect('draw', (canvasObj, ctx, w, h) => {
            this._draw(ctx, w, h, sections, width);
            return false;
        });
        this.window.set_content(canvas);
        canvas.invalidate();
        this.window.set_size(totalWidth, totalHeight);
    },

    _draw: function (ctx, w, h, sections, contentWidth) {
        ctx.save();
        ctx.setOperator(Cairo.Operator.CLEAR);
        ctx.paint();
        ctx.restore();
        ctx.setOperator(Cairo.Operator.OVER);

        // фон: мягкий вертикальный градиент + тонкая обводка для отделения от обоев
        let bgAlpha = (this.backgroundOpacity !== undefined ? this.backgroundOpacity : 205) / 255;
        this._roundedRect(ctx, 0, 0, w, h, CORNER_RADIUS);
        let bgGradient = new Cairo.LinearGradient(0, 0, 0, h);
        bgGradient.addColorStopRGBA(0, COLOR_BG_TOP[0], COLOR_BG_TOP[1], COLOR_BG_TOP[2], bgAlpha);
        bgGradient.addColorStopRGBA(1, COLOR_BG_BOTTOM[0], COLOR_BG_BOTTOM[1], COLOR_BG_BOTTOM[2], bgAlpha);
        ctx.setSource(bgGradient);
        ctx.fill();

        this._roundedRect(ctx, 0.5, 0.5, w - 1, h - 1, CORNER_RADIUS);
        ctx.setSourceRGBA(COLOR_BORDER[0], COLOR_BORDER[1], COLOR_BORDER[2], COLOR_BORDER[3]);
        ctx.setLineWidth(1);
        ctx.stroke();

        sections.forEach((section, idx) => {
            ctx.save();
            ctx.translate(MARGIN, section.y);

            this._drawSectionHeader(ctx, section.label, section.color, section.statText, contentWidth);
            ctx.translate(0, HEADER_HEIGHT);

            if (section.type === 'cpu') {
                if (section.view === 'bars') this._drawCpuBars(ctx, contentWidth);
                else if (section.view === 'graph') this._drawCpuGraph(ctx, contentWidth);
                else this._drawCpuRings(ctx);
            } else if (section.type === 'mem') this._drawMemBars(ctx, contentWidth);
            else if (section.type === 'net') {
                this._drawSparkline(ctx, contentWidth, this._netHistory.recv, this._netHistory.sent, COLOR_NET_DOWN, COLOR_NET_UP, '↓', '↑');
            } else if (section.type === 'disk') {
                this._drawDiskUsage(ctx, contentWidth);
                ctx.translate(0, section.usageHeight + BAR_SPACING);
                this._drawSparkline(ctx, contentWidth, this._diskIoHistory.read, this._diskIoHistory.write, COLOR_DISK, COLOR_DISK_WRITE, 'R', 'W');
            }
            ctx.restore();

            let isLast = idx === sections.length - 1;
            if (!isLast) {
                let dividerY = section.y + section.height + SECTION_SPACING / 2;
                ctx.setSourceRGBA(1, 1, 1, 0.06);
                ctx.setLineWidth(1);
                ctx.moveTo(MARGIN, dividerY);
                ctx.lineTo(contentWidth + MARGIN, dividerY);
                ctx.stroke();
            }
        });
    },

    _drawSectionHeader: function (ctx, label, color, statText, contentWidth) {
        ctx.setSourceRGBA(color[0], color[1], color[2], 0.9);
        ctx.arc(3, 5, 3, 0, 2 * Math.PI);
        ctx.fill();

        ctx.setSourceRGBA(COLOR_LABEL[0], COLOR_LABEL[1], COLOR_LABEL[2], COLOR_LABEL[3]);
        ctx.selectFontFace(LABEL_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.BOLD);
        ctx.setFontSize(9);
        ctx.moveTo(12, 9);
        ctx.showText(label);

        if (statText) {
            ctx.selectFontFace(NUMBER_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
            ctx.setFontSize(8.5);
            let extents = ctx.textExtents(statText);
            ctx.moveTo(contentWidth - extents.width - extents.xBearing, 9);
            ctx.showText(statText);
        }
    },

    _roundedRect: function (ctx, x, y, w, h, r) {
        ctx.newSubPath();
        ctx.arc(x + w - r, y + r, r, -Math.PI / 2, 0);
        ctx.arc(x + w - r, y + h - r, r, 0, Math.PI / 2);
        ctx.arc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
        ctx.arc(x + r, y + r, r, Math.PI, (3 * Math.PI) / 2);
        ctx.closePath();
    },

    _drawCpuRings: function (ctx) {
        let x = RING_SPACING / 2;
        let coreCount = this._cpuPercents.length;
        for (let idx = 0; idx < coreCount; idx++) {
            let percent = this._cpuSmoother.value(idx);
            let cx = x + RING_SIZE / 2;
            let cy = RING_SIZE / 2;
            let radius = RING_SIZE / 2 - RING_THICKNESS / 2;

            ctx.setLineWidth(RING_THICKNESS);
            ctx.setLineCap(Cairo.LineCap.ROUND);

            ctx.setSourceRGBA(1, 1, 1, 0.12);
            ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
            ctx.stroke();

            let color = severityColor(COLOR_CPU, percent);
            ctx.setSourceRGBA(color[0], color[1], color[2], color[3]);
            let startAngle = -Math.PI / 2;
            let endAngle = startAngle + Math.max(percent, 0.6) / 100 * 2 * Math.PI;
            ctx.newSubPath();
            ctx.arc(cx, cy, radius, startAngle, endAngle);
            ctx.stroke();

            ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
            ctx.selectFontFace(NUMBER_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.BOLD);
            ctx.setFontSize(10);
            let label = Math.round(percent).toString();
            let extents = ctx.textExtents(label);
            ctx.moveTo(cx - extents.width / 2 - extents.xBearing, cy - extents.height / 2 - extents.yBearing);
            ctx.showText(label);

            x += RING_SIZE + RING_SPACING;
        }
    },

    _drawCpuBars: function (ctx, width) {
        let coreCount = this._cpuPercents.length;
        for (let idx = 0; idx < coreCount; idx++) {
            let percent = this._cpuSmoother.value(idx);
            let y = idx * (BAR_HEIGHT + BAR_SPACING);
            let label = 'Core ' + idx + '  ' + Math.round(percent) + '%';
            this._drawBar(ctx, y, width, percent, label, severityColor(COLOR_CPU, percent), 1.0);
        }
    },

    _drawCpuGraph: function (ctx, width) {
        let plotTop = SPARK_LABEL_HEIGHT;
        let plotHeight = SPARK_HEIGHT - plotTop - 2;
        this._drawLine(ctx, this._cpuHistory, 100, width, plotTop, plotHeight, severityColor(COLOR_CPU, this._cpuAverage), true);

        ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
        ctx.selectFontFace(NUMBER_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        ctx.setFontSize(9);
        ctx.moveTo(0, SPARK_LABEL_HEIGHT - 4);
        ctx.showText('Средняя загрузка: ' + Math.round(this._cpuAverage) + '%');
    },

    _drawMemBars: function (ctx, width) {
        this._drawBar(ctx, 0, width, this._memSmoother.value, 'RAM ' + Math.round(this._memSmoother.value) + '%', severityColor(COLOR_MEM, this._memSmoother.value), 1.0);
        this._drawBar(ctx, BAR_HEIGHT + BAR_SPACING, width, this._swapSmoother.value, 'SWAP ' + Math.round(this._swapSmoother.value) + '%', COLOR_MEM, 0.5);
    },

    _drawDiskUsage: function (ctx, width) {
        this._diskPartitions.forEach((partition, idx) => {
            let y = idx * (BAR_HEIGHT + BAR_SPACING);
            let percent = this._diskSmoother.value(partition.mountpoint);
            let label = this._shortMountpoint(partition.mountpoint) + ' ' + Math.round(percent) + '%';
            this._drawBar(ctx, y, width, percent, label, severityColor(COLOR_DISK, percent), 1.0);
        });
    },

    _shortMountpoint: function (mountpoint) {
        if (mountpoint === '/') return '/';
        let parts = mountpoint.replace(/\/+$/, '').split('/');
        return parts[parts.length - 1];
    },

    _drawBar: function (ctx, y, width, percent, label, color, alpha) {
        ctx.setSourceRGBA(1, 1, 1, 0.1);
        this._roundedRect(ctx, 0, y, width, BAR_HEIGHT, BAR_HEIGHT / 2);
        ctx.fill();

        let fillWidth = Math.max((width * Math.min(Math.max(percent, 0), 100)) / 100, BAR_HEIGHT);
        let gradient = new Cairo.LinearGradient(0, y, fillWidth, y);
        gradient.addColorStopRGBA(0, color[0] * 0.65, color[1] * 0.65, color[2] * 0.65, color[3] * alpha);
        gradient.addColorStopRGBA(1, color[0], color[1], color[2], color[3] * alpha);
        this._roundedRect(ctx, 0, y, fillWidth, BAR_HEIGHT, BAR_HEIGHT / 2);
        ctx.setSource(gradient);
        ctx.fill();

        ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
        ctx.selectFontFace(NUMBER_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        ctx.setFontSize(8.5);
        let extents = ctx.textExtents(label);
        ctx.moveTo(width / 2 - extents.width / 2 - extents.xBearing, y + BAR_HEIGHT / 2 - extents.height / 2 - extents.yBearing);
        ctx.showText(label);
    },

    _drawSparkline: function (ctx, width, historyA, historyB, colorA, colorB, symbolA, symbolB) {
        let maxValue = Math.max(1, ...historyA, ...historyB);
        let plotTop = SPARK_LABEL_HEIGHT;
        let plotHeight = SPARK_HEIGHT - plotTop - 2;

        this._drawLine(ctx, historyA, maxValue, width, plotTop, plotHeight, colorA, true);
        this._drawLine(ctx, historyB, maxValue, width, plotTop, plotHeight, colorB, false);

        let currentA = historyA.length ? historyA[historyA.length - 1] : 0;
        let currentB = historyB.length ? historyB[historyB.length - 1] : 0;
        ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
        ctx.selectFontFace(SYMBOL_FONT, Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        ctx.setFontSize(9);
        let label = symbolA + (currentA / 1024).toFixed(1) + ' KB/s  ' + symbolB + (currentB / 1024).toFixed(1) + ' KB/s';
        ctx.moveTo(0, SPARK_LABEL_HEIGHT - 4);
        ctx.showText(label);
    },

    _drawLine: function (ctx, history, maxValue, width, plotTop, plotHeight, color, withFill) {
        if (history.length < 2) return;
        let step = width / (HISTORY_LEN - 1);
        let offset = HISTORY_LEN - history.length;

        let points = history.map((value, idx) => [
            (offset + idx) * step,
            plotTop + plotHeight - (value / maxValue) * plotHeight,
        ]);

        if (withFill) {
            let fillGradient = new Cairo.LinearGradient(0, plotTop, 0, plotTop + plotHeight);
            fillGradient.addColorStopRGBA(0, color[0], color[1], color[2], 0.28);
            fillGradient.addColorStopRGBA(1, color[0], color[1], color[2], 0.02);
            ctx.moveTo(points[0][0], plotTop + plotHeight);
            points.forEach((p) => ctx.lineTo(p[0], p[1]));
            ctx.lineTo(points[points.length - 1][0], plotTop + plotHeight);
            ctx.closePath();
            ctx.setSource(fillGradient);
            ctx.fill();
        }

        ctx.setSourceRGBA(color[0], color[1], color[2], color[3]);
        ctx.setLineWidth(1.6);
        ctx.setLineJoin(Cairo.LineJoin.ROUND);
        points.forEach((p, idx) => {
            if (idx === 0) ctx.moveTo(p[0], p[1]);
            else ctx.lineTo(p[0], p[1]);
        });
        ctx.stroke();
    },
};

function main(metadata, deskletId) {
    return new LinuxVisualizatorDesklet(metadata, deskletId);
}
