/* Rejestry i wykazy — Warszawa. Bez zależności, dane ładowane na żądanie. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };

  var MONTHS = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
    'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];
  var MONTHS_SHORT = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze',
    'lip', 'sie', 'wrz', 'paź', 'lis', 'gru'];

  var state = {
    index: null, district: null, year: null,
    view: 'overview', month: null, q: ''
  };

  var elDistrict = $('district');
  var elYear = $('year');
  var elTabs = $('tabs');
  var elView = $('view');
  var elCount = $('count');
  var elSource = $('source');
  var elQ = $('q');

  var D = null;                 // dane wybranego rocznika
  var byMonth = {};             // regId -> miesiąc -> wiersze
  var totals = { all: 0, byMonth: {}, byReg: {} };

  /* ------------------------------------------------------------- pomocnicze */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmt(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function fmtDate(iso) {
    if (!iso) return '';
    var p = iso.split('-');
    return p[2] + '.' + p[1] + '.' + p[0];
  }

  function norm(s) {
    return String(s == null ? '' : s)
      .toLowerCase()
      .replace(/ą/g, 'a').replace(/ć/g, 'c').replace(/ę/g, 'e')
      .replace(/ł/g, 'l').replace(/ń/g, 'n').replace(/ó/g, 'o')
      .replace(/ś/g, 's').replace(/ź/g, 'z').replace(/ż/g, 'z');
  }

  function plural(n, one, few, many) {
    if (n === 1) return one;
    var d = n % 10, h = n % 100;
    if (d >= 2 && d <= 4 && (h < 10 || h >= 20)) return few;
    return many;
  }

  function monthOf(row) {
    if (!row.d) return 0;
    var m = parseInt(row.d.slice(5, 7), 10);
    return m >= 1 && m <= 12 ? m : 0;
  }

  function badgeClass(v) {
    var t = norm(v);
    if (/^ustalam|^pnb$|^udzielam|^zatwierdz/.test(t)) return 'ok';
    if (/odmawiam|^odmowa|^sprzeciw/.test(t)) return 'no';
    if (/umorz|uchylam|^brak/.test(t)) return 'neutral';
    if (/przenies|zmieniam|^pnr$/.test(t)) return 'info';
    return 'neutral';
  }

  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' → HTTP ' + r.status);
      return r.json();
    });
  }

  /* ------------------------------------------------------------ adres w pasku */

  function readHash() {
    var p = (location.hash || '').replace(/^#\/?/, '').split('/');
    return {
      district: p[0] || null,
      year: p[1] || null,
      month: (p[2] === undefined || p[2] === '') ? null : p[2]
    };
  }

  function writeHash() {
    var h = '#/' + state.district + '/' + state.year +
            (state.view === 'month' ? '/' + state.month : '');
    if (location.hash !== h) history.replaceState(null, '', h);
  }

  /* ------------------------------------------------------------------ indeks */

  function districtEntry(slug) {
    return state.index.districts.filter(function (d) { return d.slug === slug; })[0];
  }

  function buildIndex() {
    byMonth = {};
    totals = { all: 0, byMonth: {}, byReg: {} };

    D.registers.forEach(function (reg) {
      byMonth[reg.id] = {};
      totals.byReg[reg.id] = 0;
      reg.rows.forEach(function (row) {
        var m = monthOf(row);
        (byMonth[reg.id][m] = byMonth[reg.id][m] || []).push(row);
        totals.byReg[reg.id]++;
        totals.all++;
        totals.byMonth[m] = (totals.byMonth[m] || 0) + 1;
      });
    });
  }

  function rowsFor(regId, m) {
    return (byMonth[regId] && byMonth[regId][m]) || [];
  }

  function monthTotal(m) { return totals.byMonth[m] || 0; }

  function lastMonthLabel() {
    for (var m = 12; m >= 1; m--) if (monthTotal(m) > 0) return MONTHS[m - 1];
    return '—';
  }

  /* ------------------------------------------------------------- lista wyboru */

  function renderDistricts() {
    var list = state.index.districts.slice().sort(function (a, b) {
      return a.name.localeCompare(b.name, 'pl');
    });
    elDistrict.innerHTML = list.map(function (d) {
      return '<option value="' + esc(d.slug) + '">' + esc(d.name) + '</option>';
    }).join('');
    elDistrict.value = state.district;
  }

  function renderYears() {
    var d = districtEntry(state.district);
    if (!d || !d.years.length) {
      elYear.innerHTML = '';
      elYear.disabled = true;
      return;
    }
    elYear.disabled = false;
    elYear.innerHTML = d.years.slice().reverse().map(function (y) {
      return '<option value="' + y.year + '">' + y.year + '</option>';
    }).join('');
    elYear.value = state.year;
  }

  /* ------------------------------------------------------------------- zakładki */

  function renderTabs() {
    if (!D) { elTabs.innerHTML = ''; return; }

    var html = '<button class="tab" type="button" role="tab" data-view="overview"' +
      ' aria-selected="' + (state.view === 'overview') + '">Przegląd roku</button>';

    for (var m = 1; m <= 12; m++) {
      var n = monthTotal(m);
      html += '<button class="tab' + (n === 0 ? ' is-empty' : '') + '" type="button"' +
        ' role="tab" data-month="' + m + '" aria-selected="' +
        (state.view === 'month' && state.month === m) + '">' +
        MONTHS_SHORT[m - 1] + '<span class="c">' + n + '</span></button>';
    }

    if (monthTotal(0) > 0) {
      html += '<button class="tab" type="button" role="tab" data-month="0"' +
        ' aria-selected="' + (state.view === 'month' && state.month === 0) + '">' +
        'bez daty<span class="c">' + monthTotal(0) + '</span></button>';
    }

    elTabs.innerHTML = html;
  }

  /* ------------------------------------------------------------------ przegląd */

  function kpi(n, label, accent) {
    return '<div class="kpi' + (accent ? ' is-accent' : '') + '">' +
      '<div class="n">' + n + '</div><div class="l">' + label + '</div></div>';
  }

  function renderOverview() {
    var maxCell = 1;
    D.registers.forEach(function (reg) {
      for (var m = 1; m <= 12; m++) {
        maxCell = Math.max(maxCell, rowsFor(reg.id, m).length);
      }
    });

    var activeMonths = 0;
    for (var m = 1; m <= 12; m++) if (monthTotal(m) > 0) activeMonths++;

    var html = '<div class="kpis">' +
      kpi(fmt(totals.all), 'pozycji łącznie', true) +
      kpi(D.registers.length, 'rejestrów', false) +
      kpi(activeMonths, 'miesięcy z danymi', false) +
      kpi(lastMonthLabel(), 'ostatni miesiąc z wpisami', false) +
      '</div>';

    /* macierz rejestr × miesiąc */
    html += '<div class="panel"><div class="panel-head">' +
      '<h2>Rejestry w układzie miesięcznym</h2>' +
      '<span class="sub">kliknij liczbę, aby przejść do wpisów</span>' +
      '<span class="count">' + D.year + '</span></div>' +
      '<div class="panel-body"><div class="tbl-wrap">' +
      '<table class="matrix"><thead><tr><th>Rejestr</th>';

    for (var i = 1; i <= 12; i++) html += '<th>' + MONTHS_SHORT[i - 1] + '</th>';
    if (monthTotal(0) > 0) html += '<th>bd.</th>';
    html += '<th class="total">Razem</th></tr></thead><tbody>';

    D.registers.forEach(function (reg) {
      html += '<tr><th scope="row">' + esc(reg.short) + '</th>';

      for (var mm = 1; mm <= 12; mm++) {
        var n = rowsFor(reg.id, mm).length;
        if (n === 0) {
          html += '<td class="zero">·</td>';
        } else {
          var a = 0.08 + 0.62 * (n / maxCell);
          html += '<td class="cell" data-goto="' + mm + '" data-reg="' + reg.id +
            '" style="background:rgba(47,111,79,' + a.toFixed(3) + ');color:' +
            (a > 0.42 ? '#fff' : '#1d4a33') + '" title="' + esc(reg.name) + ' — ' +
            MONTHS[mm - 1] + ': ' + n + '">' + n + '</td>';
        }
      }

      if (monthTotal(0) > 0) {
        var n0 = rowsFor(reg.id, 0).length;
        html += n0 === 0
          ? '<td class="zero">·</td>'
          : '<td class="cell" data-goto="0" data-reg="' + reg.id +
            '" style="background:#eef2f7;color:#64748b" title="bez daty: ' + n0 + '">' +
            n0 + '</td>';
      }

      html += '<td class="total">' + totals.byReg[reg.id] + '</td></tr>';
    });

    html += '</tbody></table></div></div></div>';

    /* zakres rejestrów */
    html += '<div class="panel"><div class="panel-head">' +
      '<h2>Zakres rejestrów</h2>' +
      '<span class="sub">pliki źródłowe i pokrycie dat</span></div>' +
      '<div class="panel-body"><div class="tbl-wrap">' +
      '<table class="tbl"><thead><tr><th>Rejestr</th><th class="num">Pozycji</th>' +
      '<th>Zakres dat</th><th>Plik źródłowy</th></tr></thead><tbody>';

    D.registers.forEach(function (reg) {
      var dates = reg.rows.map(function (r) { return r.d; }).filter(Boolean).sort();
      var range = dates.length
        ? fmtDate(dates[0]) + ' – ' + fmtDate(dates[dates.length - 1])
        : '<span class="muted">brak dat</span>';
      var src = reg.url
        ? '<a href="' + esc(reg.url) + '" target="_blank" rel="noopener">' +
          esc(reg.file || 'plik') + '</a>'
        : esc(reg.file || '—');

      html += '<tr><td><b>' + esc(reg.name) + '</b></td>' +
        '<td class="num">' + reg.rows.length + '</td>' +
        '<td class="date">' + range + '</td>' +
        '<td>' + src + '</td></tr>';
    });

    html += '</tbody></table></div></div></div>';

    elView.innerHTML = html;
  }

  /* -------------------------------------------------------------------- miesiąc */

  function renderMonth(m) {
    var total = monthTotal(m);
    var label = m === 0
      ? 'Pozycje bez daty'
      : MONTHS[m - 1].charAt(0).toUpperCase() + MONTHS[m - 1].slice(1) + ' ' + D.year;

    var html = '<div class="month-title"><h2>' + label + '</h2>' +
      '<span class="n">' + total + ' ' +
      plural(total, 'pozycja', 'pozycje', 'pozycji') + '</span></div>';

    if (total === 0) {
      html += '<div class="panel"><div class="empty"><b>Brak wpisów w tym miesiącu</b>' +
        'Urząd nie opublikował jeszcze danych dla tego okresu.</div></div>';
      elView.innerHTML = html;
      return;
    }

    if (m === 0) {
      html += '<div class="panel"><div class="empty" style="padding:22px">' +
        'Wpisy, dla których w pliku źródłowym nie podano daty. Zostaną przypisane ' +
        'do miesiąca, gdy urząd uzupełni rejestr.</div></div>';
    }

    D.registers.forEach(function (reg) {
      var rows = rowsFor(reg.id, m);
      if (!rows.length) return;
      html += renderRegisterPanel(reg, rows,
        m === 0 ? 'bez daty' : MONTHS[m - 1] + ' ' + D.year);
    });

    elView.innerHTML = html;
  }

  function renderRegisterPanel(reg, rows, periodLabel) {
    var h = '<div class="panel" id="reg-' + esc(reg.id) + '">' +
      '<div class="panel-head"><h2>' + esc(reg.name) + '</h2>' +
      '<span class="sub">' + esc(periodLabel) + '</span>' +
      '<span class="count">' + rows.length + '</span></div>' +
      '<div class="panel-body"><div class="tbl-wrap">' +
      '<table class="tbl"><thead><tr><th class="num">Lp.</th><th>Data</th>';

    reg.cols.forEach(function (c) { h += '<th>' + esc(c.l) + '</th>'; });
    h += '</tr></thead><tbody>';

    rows.forEach(function (row, i) {
      h += '<tr><td class="num">' + (i + 1) + '</td>' +
        '<td class="date">' + (row.d ? fmtDate(row.d) : '<span class="muted">—</span>') + '</td>';

      reg.cols.forEach(function (c) {
        var v = row.c[c.k];
        if (v == null || v === '') { h += '<td class="muted">—</td>'; return; }

        if (c.k === 'roz' || c.k === 'rodz') {
          h += '<td><span class="badge ' + badgeClass(v) + '">' + esc(v) + '</span></td>';
        } else if (c.k === 'nr') {
          h += '<td class="nr">' + esc(v) + '</td>';
        } else {
          var cls = c.w === 'wide' ? 'wide' : (c.w === 'mid' ? 'mid' : '');
          if (String(v).length > 150) {
            h += '<td class="' + cls + '"><div class="clamp">' + esc(v) + '</div>' +
              '<button class="more" type="button">więcej</button></td>';
          } else {
            h += '<td class="' + cls + '">' + esc(v) + '</td>';
          }
        }
      });

      h += '</tr>';
    });

    h += '</tbody></table></div></div></div>';
    return h;
  }

  /* ---------------------------------------------------------------- wyszukiwanie */

  function renderSearch(q) {
    var nq = norm(q);
    var hits = [];

    D.registers.forEach(function (reg) {
      reg.rows.forEach(function (row) {
        var hay = norm(reg.name + ' ' + Object.keys(row.c).map(function (k) {
          return row.c[k];
        }).join(' '));
        if (hay.indexOf(nq) !== -1) hits.push({ reg: reg, row: row });
      });
    });

    var html = '<div class="month-title"><h2>Wyniki wyszukiwania</h2>' +
      '<span class="n">„' + esc(q) + '” — ' + hits.length + ' ' +
      plural(hits.length, 'pozycja', 'pozycje', 'pozycji') + '</span></div>';

    if (!hits.length) {
      html += '<div class="panel"><div class="empty"><b>Nic nie znaleziono</b>' +
        'Spróbuj krótszej frazy, np. nazwy ulicy lub wnioskodawcy.</div></div>';
      elView.innerHTML = html;
      return;
    }

    var grouped = {};
    hits.forEach(function (h) {
      (grouped[h.reg.id] = grouped[h.reg.id] || []).push(h.row);
    });

    D.registers.forEach(function (reg) {
      if (!grouped[reg.id]) return;
      html += renderRegisterPanel(reg, grouped[reg.id], 'wyniki wyszukiwania');
    });

    elView.innerHTML = html;
  }

  /* ---------------------------------------------------------------------- źródło */

  function renderSource() {
    if (!D) { elSource.innerHTML = ''; return; }
    var d = districtEntry(state.district);
    var bits = [];
    if (d && d.sources && d.sources.length) {
      bits.push('źródła: ' + d.sources.map(esc).join(', '));
    }
    bits.push('wygenerowano ' + esc(D.generated.slice(0, 10)));
    elSource.innerHTML = bits.join(' · ');
  }

  /* ---------------------------------------------------------------------- rysowanie */

  function draw() {
    renderYears();
    renderTabs();

    if (state.q.trim().length >= 2) {
      renderSearch(state.q.trim());
      elCount.textContent = '';
    } else if (state.view === 'month') {
      renderMonth(state.month);
      elCount.textContent = fmt(monthTotal(state.month)) + ' ' +
        plural(monthTotal(state.month), 'pozycja', 'pozycje', 'pozycji');
    } else {
      renderOverview();
      elCount.textContent = fmt(totals.all) + ' ' +
        plural(totals.all, 'pozycja', 'pozycje', 'pozycji') +
        ' w ' + D.registers.length + ' rejestrach';
    }

    renderSource();
    writeHash();
  }

  /* ---------------------------------------------------------------------- ładowanie */

  function loadYear() {
    elView.innerHTML = '<p class="empty">Wczytywanie…</p>';
    var url = 'data/' + state.district + '/' + state.year + '.json';

    return getJSON(url).then(function (data) {
      D = data;
      buildIndex();
      draw();
    }).catch(function (e) {
      D = null;
      elTabs.innerHTML = '';
      elCount.textContent = '';
      elView.innerHTML = '<p class="error">Nie udało się wczytać danych: ' +
        esc(e.message) + '</p>';
    });
  }

  function selectDistrict(slug) {
    var d = districtEntry(slug);
    if (!d) return;
    state.district = slug;
    state.year = d.default;
    state.view = 'overview';
    state.month = null;
    state.q = '';
    elQ.value = '';
    elDistrict.value = slug;
    renderYears();
    return loadYear();
  }

  function selectYear(year) {
    state.year = Number(year);
    state.view = 'overview';
    state.month = null;
    state.q = '';
    elQ.value = '';
    return loadYear();
  }

  /* ---------------------------------------------------------------------- zdarzenia */

  elDistrict.addEventListener('change', function () { selectDistrict(this.value); });

  elYear.addEventListener('change', function () { selectYear(this.value); });

  elTabs.addEventListener('click', function (e) {
    var t = e.target.closest('.tab');
    if (!t) return;

    if (t.dataset.view === 'overview') {
      state.view = 'overview';
      state.month = null;
    } else {
      state.view = 'month';
      state.month = parseInt(t.dataset.month, 10);
    }

    state.q = '';
    elQ.value = '';
    draw();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  elView.addEventListener('click', function (e) {
    var cell = e.target.closest('td.cell');
    if (cell) {
      state.view = 'month';
      state.month = parseInt(cell.dataset.goto, 10);
      state.q = '';
      elQ.value = '';
      draw();
      var target = document.getElementById('reg-' + cell.dataset.reg);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    var more = e.target.closest('.more');
    if (more) {
      var box = more.previousElementSibling;
      box.classList.toggle('open');
      more.textContent = box.classList.contains('open') ? 'mniej' : 'więcej';
    }
  });

  var timer = null;
  elQ.addEventListener('input', function () {
    var v = this.value;
    clearTimeout(timer);
    timer = setTimeout(function () { state.q = v; draw(); }, 160);
  });

  window.addEventListener('hashchange', function () {
    var h = readHash();
    if (h.district && h.district !== state.district) {
      var p = selectDistrict(h.district);
      if (p && p.then) p.then(function () { if (h.year) selectYear(h.year); });
    }
  });

  /* ---------------------------------------------------------------------- start */

  getJSON('data/index.json').then(function (index) {
    state.index = index;

    var h = readHash();
    var withData = index.districts.filter(function (d) { return d.years.length; });
    if (!withData.length) throw new Error('manifest bez danych');

    var start = withData.filter(function (d) { return d.slug === h.district; })[0] ||
                withData.filter(function (d) { return d.slug === 'ursus'; })[0] ||
                withData[0];

    state.district = start.slug;

    var wanted = h.year && start.years.filter(function (y) {
      return String(y.year) === h.year;
    })[0];
    state.year = wanted ? Number(h.year) : start.default;

    if (h.month !== null && /^\d{1,2}$/.test(h.month)) {
      state.view = 'month';
      state.month = parseInt(h.month, 10);
    }

    renderDistricts();
    return loadYear();
  }).catch(function (e) {
    var hint = '';
    if (location.protocol === 'file:') {
      hint = '<br><br>Plik otwarty spod <code>file://</code> — w tym trybie ' +
             'przeglądarka blokuje pobieranie danych (<code>fetch()</code>). ' +
             'Uruchom podgląd przez HTTP: ' +
             '<code>python -m http.server --directory site</code> ' +
             'i wejdź na <a href="http://localhost:8000/">localhost:8000</a>.';
    }
    elView.innerHTML = '<p class="error">Nie udało się wczytać manifestu: ' +
      esc(e.message) + hint + '</p>';
  });
})();
