(function () {
    var data = window.dashboardData || {};
    var estimationData  = data.estimationData  || [];
    var forecastData    = data.forecastData    || [];
    var historyData     = data.historyData     || [];
    var forecastMetrics = data.forecastMetrics || {};
    var hiddenPackageIds = [80, 82, 83];
    var packageIds = (data.packageIds || [])
        .filter(function(pid) { return hiddenPackageIds.indexOf(Number(pid)) === -1; });
    var currentPackageId = packageIds.length ? Number(packageIds[0]) : null;
    var dailyUtilVisible = false;

    function roundToNearestInteger(value) {
        var num = Number(value);
        return Number.isFinite(num) ? Math.round(num) : 0;
    }

    function fmtOriginalValue(value) {
        var num = Number(value);
        if (!Number.isFinite(num)) return value;
        return num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
    }

    function sortByDateAscending(rows) {
        return rows.slice().sort(function(a, b) { return a.date.localeCompare(b.date); });
    }

    function getLineYAxisMax(values) {
        var nums = values.map(Number).filter(Number.isFinite);
        var rawMax = nums.length ? Math.max.apply(null, nums) : 0;
        return Math.max(Math.ceil(rawMax / 10) * 10, 10);
    }

    function getLineYAxisRangeMax(yMax) {
        return yMax + Math.max(yMax * 0.02, 1);
    }

    function getMetricValue(value, isPercent) {
        var num = Number(value);
        if (!Number.isFinite(num)) return '-';
        return num.toLocaleString('id-ID', {
            minimumFractionDigits: 0,
            maximumFractionDigits: isPercent ? 2 : 4,
        }) + (isPercent ? '%' : '');
    }

    function getPackageMetrics(pkgId) {
        if (pkgId === null || pkgId === undefined) return { subscribe: {}, terminate: {} };
        return forecastMetrics[String(Number(pkgId))] || forecastMetrics[Number(pkgId)] || { subscribe: {}, terminate: {} };
    }

    function aggregateMonthlyAvg(rows, valueKey) {
        var monthly = {};
        rows.forEach(function(row) {
            var monthDate = row.date.substring(0, 7) + '-01';
            if (!monthly[monthDate]) monthly[monthDate] = { date: monthDate, sum: 0, count: 0 };
            monthly[monthDate].sum   += Number(row[valueKey]) || 0;
            monthly[monthDate].count += 1;
        });
        return Object.values(monthly)
            .map(function(m) {
                var r = { date: m.date };
                r[valueKey] = m.count > 0 ? Math.round((m.sum / m.count) * 100) / 100 : 0;
                return r;
            })
            .sort(function(a, b) { return a.date.localeCompare(b.date); });
    }

    function renderUtilizationChart(rows) {
        var div = document.getElementById('utilizationChart');
        if (!div) return;
        var monthly = aggregateMonthlyAvg(rows, 'utilization');

        if (historyData.length) {
            var allHistDates = historyData.map(function(r) { return r.date; }).sort();
            var lastHistMonth = allHistDates[allHistDates.length - 1].substring(0, 7);
            monthly = monthly.filter(function(m) {
                return m.date.substring(0, 7) > lastHistMonth;
            });
        }
        var values  = monthly.map(function(r) { return r.utilization; });
        var rawMax  = values.length ? Math.max.apply(null, values) : 0;
        var yMax    = Math.max(rawMax * 1.2, 95);
        Plotly.react(div, [{
            x: monthly.map(function(r) { return r.date; }),
            y: values,
            type: 'bar',
            name: 'Utilisasi (%)',
            marker: { color: '#3b5bdb', opacity: 0.85 },
            hovertemplate: '<b>%{x|%b %Y}</b><br>Rata-rata Utilisasi: <b>%{y:.1f}%</b><extra></extra>',
        }], {
            paper_bgcolor: 'white', plot_bgcolor: 'white', bargap: 0.25,
            margin: { t: 10, r: 20, b: 70, l: 70 },
            xaxis: { type: 'date', tickformat: '%b %Y', showgrid: false,
                     title: { text: 'Bulan', font: { size: 11, color: '#6b7280' } } },
            yaxis: { ticksuffix: '%', range: [0, yMax], gridcolor: 'rgba(0,0,0,.07)' },
            shapes: [{ type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: 80, y1: 80,
                       line: { color: '#f0a828', dash: 'dash', width: 2 } }],
            legend: { orientation: 'h', x: 0, y: -0.3 },
            hovermode: 'closest',
            hoverlabel: { bgcolor: '#111827', bordercolor: 'rgba(255,255,255,0.12)',
                          font: { color: 'white', size: 12 }, align: 'left' },
        }, { responsive: true, displayModeBar: false });
    }

    function renderDailyUtilizationChart(rows) {
        var div = document.getElementById('utilizationDailyChart');
        if (!div || !rows.length) return;
        var sorted = rows.slice().sort(function(a, b) { return a.date.localeCompare(b.date); });
        var values = sorted.map(function(r) { return Math.round(Number(r.utilization) * 100) / 100; });
        var rawMax = Math.max.apply(null, values);
        var yMax   = Math.max(Math.ceil(rawMax / 10) * 10, 95);
        var xDates = sorted.map(function(r) { return r.date; });
        var totalDays = (new Date(xDates[xDates.length - 1]) - new Date(xDates[0])) / 86400000;
        var dtick = totalDays <= 30  ? 7  * 86400000 :
                    totalDays <= 120 ? 14 * 86400000 :
                    'M1';
        Plotly.react(div, [{
            x: xDates,
            y: values,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Utilisasi Harian',
            line: { color: '#3b5bdb', width: 2.5 },
            marker: { color: '#3b5bdb', size: 5 },
            hovertemplate: '<b>%{x|%d %b %Y}</b><br>Utilisasi: <b>%{y:.1f}%</b><extra></extra>',
        }], {
            paper_bgcolor: 'white', plot_bgcolor: 'white',
            margin: { t: 10, r: 20, b: 80, l: 65 },
            xaxis: {
                type: 'date',
                range: [xDates[0], xDates[xDates.length - 1]],
                tick0: xDates[0],
                dtick: dtick,
                title: { text: 'Tanggal', font: { size: 11 } },
                tickangle: -30, tickformat: '%d %b %Y', showgrid: false,
            },
            yaxis: {
                title: { text: 'Utilisasi (%)', font: { size: 11 } },
                ticksuffix: '%',
                range: [0, yMax + Math.max(yMax * 0.02, 1)],
                gridcolor: 'rgba(0,0,0,.07)',
            },
            shapes: [{ type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1, y0: 80, y1: 80,
                       line: { color: '#f0a828', dash: 'dash', width: 2 } }],
            legend: { orientation: 'h', x: 0, y: -0.35 },
            hovermode: 'closest',
            hoverlabel: { bgcolor: '#111827', bordercolor: 'rgba(255,255,255,0.12)',
                          font: { color: 'white', size: 12 }, align: 'left' },
        }, { responsive: true, displayModeBar: false });
    }

    function getUtilizationFilterValues() {
        var s = document.getElementById('hist-start-date');
        var e = document.getElementById('hist-end-date');
        return { start: s ? s.value : '', end: e ? e.value : '' };
    }

    function getFilteredEstimationData() {
        var f = getUtilizationFilterValues();
        return sortByDateAscending(estimationData).filter(function(row) {
            return (!f.start || row.date >= f.start) && (!f.end || row.date <= f.end);
        });
    }

    function syncUtilizationFilterBounds() {
        var s = document.getElementById('hist-start-date');
        var e = document.getElementById('hist-end-date');
        if (!s || !e || !estimationData.length) return;
        var sorted = sortByDateAscending(estimationData).map(function(r) { return r.date; });

        var firstFullMonthDate = sorted[0];
        if (historyData.length) {
            var allHistDates = historyData.map(function(r) { return r.date; }).sort();
            var lastHistMonth = allHistDates[allHistDates.length - 1].substring(0, 7); // "YYYY-MM"
            var parts = lastHistMonth.split('-');
            var y = parseInt(parts[0]), m = parseInt(parts[1]);
            m += 1;
            if (m > 12) { m = 1; y += 1; }
            firstFullMonthDate = y + '-' + (m < 10 ? '0' + m : m) + '-01';
        }

        s.min = firstFullMonthDate; s.max = sorted[sorted.length - 1];
        e.min = firstFullMonthDate; e.max = sorted[sorted.length - 1];
        if (!s.value || s.value < firstFullMonthDate) s.value = firstFullMonthDate;
        if (!e.value) e.value = sorted[sorted.length - 1];
    }

    function showFilterToast() {
        var el = document.getElementById('filterAppliedToast');
        if (!el) return;
        bootstrap.Toast.getOrCreateInstance(el, { delay: 2500 }).show();
    }

    window.applyUtilizationFilter = function() {
        var f = getUtilizationFilterValues();
        if (f.start && f.end && f.start > f.end) {
            var tmp = f.start; f.start = f.end; f.end = tmp;
            document.getElementById('hist-start-date').value = f.start;
            document.getElementById('hist-end-date').value   = f.end;
        }
        renderDailyUtilizationChart(getFilteredEstimationData());
        showFilterToast();
    };

    window.resetUtilizationFilter = function() {
        var s = document.getElementById('hist-start-date');
        var e = document.getElementById('hist-end-date');
        var sorted = sortByDateAscending(estimationData).map(function(r) { return r.date; });
        if (s && sorted.length) s.value = sorted[0];
        if (e && sorted.length) e.value = sorted[sorted.length - 1];
        renderDailyUtilizationChart(sortByDateAscending(estimationData));
    };

    window.toggleDailyUtilization = function() {
        dailyUtilVisible = !dailyUtilVisible;
        var section = document.getElementById('utilizationDailySection');
        var icon    = document.getElementById('icon-toggle-daily');
        var text    = document.getElementById('text-toggle-daily');
        if (dailyUtilVisible) {
            section.classList.remove('d-none');
            icon.className   = 'fa-solid fa-chevron-up me-1';
            text.textContent = 'Sembunyikan Detail';
            syncUtilizationFilterBounds();
            renderDailyUtilizationChart(getFilteredEstimationData());
        } else {
            section.classList.add('d-none');
            icon.className   = 'fa-solid fa-chevron-down me-1';
            text.textContent = 'Lihat Detail Per Hari';
        }
    };

    function aggregateMonthlySum(rows, valueKeys) {
        var monthly = {};
        rows.forEach(function(row) {
            var monthDate = row.date.substring(0, 7) + '-01';
            if (!monthly[monthDate]) {
                monthly[monthDate] = { date: monthDate };
                valueKeys.forEach(function(k) { monthly[monthDate][k] = 0; });
            }
            valueKeys.forEach(function(k) { monthly[monthDate][k] += Number(row[k]) || 0; });
        });
        return Object.values(monthly).sort(function(a, b) { return a.date.localeCompare(b.date); });
    }

    function getPackageData(pkgId) {
        var pid  = parseInt(pkgId);
        var hist = historyData.filter(function(r) { return r.package_id === pid; });
        var fcst = forecastData.filter(function(r) { return r.package_id === pid; });

        hist.sort(function(a, b) { return a.date.localeCompare(b.date); });
        fcst.sort(function(a, b) { return a.date.localeCompare(b.date); });

        var maxHistDate = hist.length ? hist[hist.length - 1].date : null;

        if (maxHistDate) {
            var d = new Date(maxHistDate);
            d.setFullYear(d.getFullYear() - 1);
            var oneYearBack = d.toISOString().substring(0, 10);
            hist = hist.filter(function(r) { return r.date >= oneYearBack; });
            fcst = fcst.filter(function(r) { return r.date >= oneYearBack; });
        }

        var histM = aggregateMonthlySum(hist, ['total_subscribe', 'total_terminate']);
        var fcstM = aggregateMonthlySum(fcst, ['forecast_subscribe', 'forecast_terminate']);

        return {
            histDates: histM.map(function(r) { return r.date; }),
            histSub:   histM.map(function(r) { return r.total_subscribe; }),
            histTrm:   histM.map(function(r) { return r.total_terminate; }),
            fcstDates: fcstM.map(function(r) { return r.date; }),
            fcstSub:   fcstM.map(function(r) { return r.forecast_subscribe; }),
            fcstTrm:   fcstM.map(function(r) { return r.forecast_terminate; }),
        };
    }

    function lineLayout(yTitle, yMax) {
        return {
            paper_bgcolor: 'white', plot_bgcolor: 'white',
            margin: { t: 10, r: 20, b: 80, l: 65 },
            xaxis: {
                type: 'date',
                title: { text: 'Periode Waktu (Bulan)', font: { size: 11 } },
                tickangle: -30, tickformat: '%b %Y', showgrid: false,
            },
            yaxis: {
                title: { text: yTitle, font: { size: 11 } },
                range: [0, getLineYAxisRangeMax(yMax)],
                dtick: yMax <= 10 ? 5 : 10,
                gridcolor: 'rgba(0,0,0,.07)',
            },
            legend: { orientation: 'h', x: 0, y: -0.35 },
            hovermode: 'closest',
            hoverlabel: { bgcolor: '#111827', bordercolor: 'rgba(255,255,255,0.12)',
                          font: { color: 'white', size: 12 }, align: 'left' },
        };
    }

    var HISTORIS_COLOR = '#9ca3af';

    function buildPlotlyLine(divId, histDates, histVals, fcstDates, fcstVals, yTitle, forecastColor) {
        var div = document.getElementById(divId);
        if (!div) return;
        var roundedHistVals    = histVals.map(roundToNearestInteger);
        var roundedFcstVals    = fcstVals.map(roundToNearestInteger);
        var histOriginalValues = histVals.map(fmtOriginalValue);
        var fcstOriginalValues = fcstVals.map(fmtOriginalValue);
        var yMax = getLineYAxisMax(histVals.concat(fcstVals));
        Plotly.react(div, [
            {
                x: histDates, y: roundedHistVals, customdata: histOriginalValues,
                type: 'scatter', mode: 'lines+markers', name: 'Historis',
                line: { color: HISTORIS_COLOR, width: 2.5 }, marker: { color: HISTORIS_COLOR, size: 6 },
                hovertemplate: '<b>%{x|%b %Y}</b><br>Historis: <b>%{customdata}</b><extra></extra>',
            },
            {
                x: fcstDates, y: roundedFcstVals, customdata: fcstOriginalValues,
                type: 'scatter', mode: 'lines+markers', name: 'Forecast',
                line: { color: forecastColor, width: 2.5 }, marker: { color: forecastColor, size: 6 },
                hovertemplate: '<b>%{x|%b %Y}</b><br>Forecast: <b>%{customdata}</b><extra></extra>',
            },
        ], lineLayout(yTitle, yMax), { responsive: true, displayModeBar: false });
    }

    function renderMetricSummary(pkgId) {
        var container = document.getElementById('forecastMetricsSummary');
        if (!container) return;
        var metrics = getPackageMetrics(pkgId);
        var sections = [
            { label: 'Subscribe', metrics: metrics.subscribe || {}, color: '#3b5bdb' },
            { label: 'Terminate', metrics: metrics.terminate || {}, color: '#ef4444' },
        ];
        container.innerHTML = sections.map(function(s) {
            return '<div class="col-lg-6">' +
                '<div class="border rounded-4 p-3 h-100" style="background:#f8fafc; border-color:rgba(148,163,184,.35) !important;">' +
                    '<div class="d-flex align-items-center justify-content-between mb-3">' +
                        '<div>' +
                            '<div class="text-muted small">Ringkasan ' + s.label + '</div>' +
                            '<div class="fw-bold">Error ' + s.label + '</div>' +
                        '</div>' +
                        '<span class="badge rounded-pill" style="background:' + s.color + '1a;color:' + s.color + ';border:1px solid ' + s.color + '33;">' + s.label + '</span>' +
                    '</div>' +
                    '<div class="row g-2">' +
                        metricCard('MAE',   s.metrics.mae,   false) +
                        metricCard('RMSE',  s.metrics.rmse,  false) +
                        metricCard('SMAPE', s.metrics.smape, true)  +
                    '</div>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    function metricCard(label, value, isPercent) {
        return '<div class="col-4">' +
            '<div class="border rounded-3 p-2 h-100" style="background:#fff; border-color:rgba(148,163,184,.28) !important;">' +
                '<div class="text-muted" style="font-size:.72rem;">' + label + '</div>' +
                '<div class="fw-semibold">' + getMetricValue(value, isPercent) + '</div>' +
            '</div>' +
        '</div>';
    }

    function renderCurrentPackageCharts() {
        if (!currentPackageId) return;
        var data = getPackageData(currentPackageId);
        renderMetricSummary(currentPackageId);
        buildPlotlyLine('subscribeChart',
            data.histDates, data.histSub, data.fcstDates, data.fcstSub,
            'Jumlah Subscription VM', '#3b5bdb');
        buildPlotlyLine('terminateChart',
            data.histDates, data.histTrm, data.fcstDates, data.fcstTrm,
            'Jumlah Terminasi VM', '#ef4444');
    }

    window.updateLineCharts = function(pkgId) {
        if (!pkgId && packageIds.length) pkgId = packageIds[0];
        if (!pkgId) return;
        currentPackageId = Number(pkgId);
        renderCurrentPackageCharts();
    };

    if (estimationData.length) {
        renderUtilizationChart(sortByDateAscending(estimationData));
    }
    if (packageIds.length) {
        renderCurrentPackageCharts();
    }
}());
