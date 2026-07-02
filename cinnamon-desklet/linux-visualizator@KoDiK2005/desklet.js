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
const COLOR_BG = [20 / 255, 20 / 255, 25 / 255, 180 / 255];
const COLOR_TEXT = [224 / 255, 224 / 255, 224 / 255, 1];
const COLOR_CPU = [0x4f / 255, 0xc3 / 255, 0xf7 / 255, 1];
const COLOR_MEM = [0x81 / 255, 0xc7 / 255, 0x84 / 255, 1];
const COLOR_NET_DOWN = [0xff / 255, 0xb7 / 255, 0x4d / 255, 1];
const COLOR_NET_UP = COLOR_CPU;
const COLOR_DISK = [0xba / 255, 0x68 / 255, 0xc8 / 255, 1];
const COLOR_DISK_WRITE = [0xe5 / 255, 0x73 / 255, 0x73 / 255, 1];

// ---- геометрия ----
const RING_SIZE = 34;
const RING_SPACING = 6;
const RING_THICKNESS = 4;
const BAR_HEIGHT = 12;
const BAR_SPACING = 4;
const SPARK_HEIGHT = 40;
const SPARK_LABEL_HEIGHT = 14;
const HISTORY_LEN = 60;
const SECTION_SPACING = 10;
const MARGIN = 16;
const MIN_PARTITION_BYTES = 1 * 1024 * 1024 * 1024;
const DISK_DEVICE_RE = /^(sd[a-z]+|nvme\d+n\d+|mmcblk\d+|vd[a-z]+)$/;

function readFile(path) {
    try {
        let [ok, contents] = GLib.file_get_contents(path);
        return ok ? ByteArray.toString(contents) : null;
    } catch (e) {
        return null;
    }
}

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

function collectNetwork(prevState, elapsedSec) {
    let text = readFile('/proc/net/dev');
    if (!text) return { recvRate: 0, sentRate: 0, state: prevState };

    let totalRx = 0;
    let totalTx = 0;
    for (let line of text.split('\n').slice(2)) {
        line = line.trim();
        if (!line) continue;
        let parts = line.split(/[:\s]+/);
        if (parts.length < 10) continue;
        if (parts[0] === 'lo') continue;
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
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-cpu', 'showCpu', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-mem', 'showMem', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-net', 'showNet', this._onSettingsChanged);
        this.settings.bindProperty(Settings.BindingDirection.IN, 'show-disk', 'showDisk', this._onSettingsChanged);

        this._cpuState = {};
        this._netState = null;
        this._diskIoState = null;
        this._lastTickTime = null;

        this._cpuPercents = [];
        this._memPercent = 0;
        this._swapPercent = 0;
        this._diskPartitions = [];
        this._netHistory = { recv: [], sent: [] };
        this._diskIoHistory = { read: [], write: [] };

        this.window = new Clutter.Actor();
        this.setContent(this.window);

        this._tick();
    },

    on_desklet_removed: function () {
        if (this._timeoutId) {
            Mainloop.source_remove(this._timeoutId);
        }
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
        }
        if (this.showMem) {
            let mem = collectMemory();
            this._memPercent = mem.percent;
            this._swapPercent = mem.swapPercent;
        }
        if (this.showNet) {
            let net = collectNetwork(this._netState, elapsed);
            this._netState = net.state;
            this._pushHistory(this._netHistory.recv, net.recvRate);
            this._pushHistory(this._netHistory.sent, net.sentRate);
        }
        if (this.showDisk) {
            this._diskPartitions = collectDiskUsage();
            let io = collectDiskIo(this._diskIoState, elapsed);
            this._diskIoState = io.state;
            this._pushHistory(this._diskIoHistory.read, io.readRate);
            this._pushHistory(this._diskIoHistory.write, io.writeRate);
        }

        this._lastTickTime = now;
        this._render();

        let intervalMs = Math.max(200, this.refreshInterval || 1000);
        this._timeoutId = Mainloop.timeout_add(intervalMs, Lang.bind(this, this._tick));
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
            let ringsWidth = this._cpuPercents.length * (RING_SIZE + RING_SPACING) + RING_SPACING;
            width = Math.max(width, ringsWidth);
            let h = RING_SIZE + 8;
            sections.push({ type: 'cpu', y, height: h });
            y += h + SECTION_SPACING;
        }
        if (this.showMem) {
            let h = BAR_HEIGHT * 2 + BAR_SPACING;
            sections.push({ type: 'mem', y, height: h });
            y += h + SECTION_SPACING;
        }
        if (this.showNet) {
            sections.push({ type: 'net', y, height: SPARK_HEIGHT });
            y += SPARK_HEIGHT + SECTION_SPACING;
        }
        if (this.showDisk) {
            let count = Math.max(this._diskPartitions.length, 1);
            let usageHeight = count * BAR_HEIGHT + (count - 1) * BAR_SPACING;
            sections.push({ type: 'disk_usage', y, height: usageHeight });
            y += usageHeight + SECTION_SPACING;
            sections.push({ type: 'disk_io', y, height: SPARK_HEIGHT });
            y += SPARK_HEIGHT + SECTION_SPACING;
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

        this._roundedRect(ctx, 0, 0, w, h, 12);
        ctx.setSourceRGBA(COLOR_BG[0], COLOR_BG[1], COLOR_BG[2], COLOR_BG[3]);
        ctx.fill();

        for (let section of sections) {
            ctx.save();
            ctx.translate(MARGIN, section.y);
            if (section.type === 'cpu') this._drawCpuRings(ctx);
            else if (section.type === 'mem') this._drawMemBars(ctx, contentWidth);
            else if (section.type === 'net') {
                this._drawSparkline(ctx, contentWidth, this._netHistory.recv, this._netHistory.sent, COLOR_NET_DOWN, COLOR_NET_UP, '↓', '↑');
            } else if (section.type === 'disk_usage') this._drawDiskUsage(ctx, contentWidth);
            else if (section.type === 'disk_io') {
                this._drawSparkline(ctx, contentWidth, this._diskIoHistory.read, this._diskIoHistory.write, COLOR_DISK, COLOR_DISK_WRITE, 'R', 'W');
            }
            ctx.restore();
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
        let x = RING_SPACING;
        for (let percent of this._cpuPercents) {
            let cx = x + RING_SIZE / 2;
            let cy = RING_SIZE / 2;
            let radius = RING_SIZE / 2 - RING_THICKNESS / 2;

            ctx.setLineWidth(RING_THICKNESS);
            ctx.setLineCap(Cairo.LineCap.ROUND);

            ctx.setSourceRGBA(1, 1, 1, 0.16);
            ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
            ctx.stroke();

            ctx.setSourceRGBA(COLOR_CPU[0], COLOR_CPU[1], COLOR_CPU[2], COLOR_CPU[3]);
            let startAngle = -Math.PI / 2;
            let endAngle = startAngle + (percent / 100) * 2 * Math.PI;
            ctx.newSubPath();
            ctx.arc(cx, cy, radius, startAngle, endAngle);
            ctx.stroke();

            ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
            ctx.selectFontFace('Monospace', Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
            ctx.setFontSize(9);
            let label = Math.round(percent).toString();
            let extents = ctx.textExtents(label);
            ctx.moveTo(cx - extents.width / 2 - extents.xBearing, cy - extents.height / 2 - extents.yBearing);
            ctx.showText(label);

            x += RING_SIZE + RING_SPACING;
        }
    },

    _drawMemBars: function (ctx, width) {
        this._drawBar(ctx, 0, width, this._memPercent, 'RAM ' + Math.round(this._memPercent) + '%', COLOR_MEM, 1.0);
        this._drawBar(ctx, BAR_HEIGHT + BAR_SPACING, width, this._swapPercent, 'SWAP ' + Math.round(this._swapPercent) + '%', COLOR_MEM, 0.55);
    },

    _drawDiskUsage: function (ctx, width) {
        this._diskPartitions.forEach((partition, idx) => {
            let y = idx * (BAR_HEIGHT + BAR_SPACING);
            let label = this._shortMountpoint(partition.mountpoint) + ' ' + Math.round(partition.percent) + '%';
            this._drawBar(ctx, y, width, partition.percent, label, COLOR_DISK, 1.0);
        });
    },

    _shortMountpoint: function (mountpoint) {
        if (mountpoint === '/') return '/';
        let parts = mountpoint.replace(/\/+$/, '').split('/');
        return parts[parts.length - 1];
    },

    _drawBar: function (ctx, y, width, percent, label, color, alpha) {
        ctx.setSourceRGBA(1, 1, 1, 0.12);
        this._roundedRect(ctx, 0, y, width, BAR_HEIGHT, 4);
        ctx.fill();

        let fillWidth = (width * Math.min(Math.max(percent, 0), 100)) / 100;
        ctx.setSourceRGBA(color[0], color[1], color[2], color[3] * alpha);
        this._roundedRect(ctx, 0, y, Math.max(fillWidth, 1), BAR_HEIGHT, 4);
        ctx.fill();

        ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
        ctx.selectFontFace('Monospace', Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        ctx.setFontSize(8);
        let extents = ctx.textExtents(label);
        ctx.moveTo(width / 2 - extents.width / 2 - extents.xBearing, y + BAR_HEIGHT / 2 - extents.height / 2 - extents.yBearing);
        ctx.showText(label);
    },

    _drawSparkline: function (ctx, width, historyA, historyB, colorA, colorB, symbolA, symbolB) {
        let maxValue = Math.max(1, ...historyA, ...historyB);
        let plotTop = SPARK_LABEL_HEIGHT;
        let plotHeight = SPARK_HEIGHT - plotTop - 2;

        this._drawLine(ctx, historyA, maxValue, width, plotTop, plotHeight, colorA);
        this._drawLine(ctx, historyB, maxValue, width, plotTop, plotHeight, colorB);

        let currentA = historyA.length ? historyA[historyA.length - 1] : 0;
        let currentB = historyB.length ? historyB[historyB.length - 1] : 0;
        ctx.setSourceRGBA(COLOR_TEXT[0], COLOR_TEXT[1], COLOR_TEXT[2], COLOR_TEXT[3]);
        ctx.selectFontFace('Monospace', Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        ctx.setFontSize(9);
        let label = symbolA + (currentA / 1024).toFixed(1) + ' KB/s  ' + symbolB + (currentB / 1024).toFixed(1) + ' KB/s';
        ctx.moveTo(0, SPARK_LABEL_HEIGHT - 4);
        ctx.showText(label);
    },

    _drawLine: function (ctx, history, maxValue, width, plotTop, plotHeight, color) {
        if (history.length < 2) return;
        let step = width / (HISTORY_LEN - 1);
        let offset = HISTORY_LEN - history.length;

        ctx.setSourceRGBA(color[0], color[1], color[2], color[3]);
        ctx.setLineWidth(1.5);
        history.forEach((value, idx) => {
            let x = (offset + idx) * step;
            let y = plotTop + plotHeight - (value / maxValue) * plotHeight;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    },
};

function main(metadata, deskletId) {
    return new LinuxVisualizatorDesklet(metadata, deskletId);
}
