/* Rejestry i wykazy — Warszawa. Bez zależności, dane ładowane na żądanie. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var state = { index: null, district: null, year: null, reg: null, data: null, q: '' };

  var elDistrict = $('district');
  var elYears = $('years');
  var elTabs = $('tabs');
  var elTable = $('table');
  var elCount = $('count');
  var elSource = $('source');
  var elQ = $('q');

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmt(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' '); }

  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(url + ' → HTTP ' + r.status);
      return r.json();
    });
  }

  /* ---------- adres w pasku ---------- */

  function readHash() {
    var p = (location.hash || '').replace(/^#\/?/, '').split('/');
    return { district: p[0] || null, year: p[1] || null, reg: p[2] || null };
  }

  function writeHash() {
    var h = '#/' + state.district + '/' + state.year + '/' + (state.reg || '');
    if (location.hash !== h) history.replaceState(null, '', h);
  }

  /* ---------- dzielnice ---------- */

  function districtEntry(slug) {
    return state.index.districts.filter(function (d) { return d.slug === slug; })[0];
  }

  function renderDistricts() {
    var list = state.index.districts.slice().sort(function (a, b) {
      return a.name.localeCompare(b.name, 'pl');
    });
    elDistrict.innerHTML = list.map(function (d) {
      return '<option value="' + esc(d.slug) + '">' + esc(d.name) +
             ' — ' + fmt(d.total) + '</option>';
    }).join('');
    elDistrict.value = state.district;
  }

  /* ---------- roczniki ---------- */

  function renderYears() {
    var d = districtEntry(state.district);
    if (!d || !d.years.length) {
      elYears.innerHTML = '<span class="count">brak danych</span>';
      return;
    }
    elYears.innerHTML = d.years.map(function (y) {
      return '<button class="year" type="button" data-year="' + y.year + '"' +
             ' aria-pressed="' + (y.year === state.year) + '">' + y.year +
             '<span class="n">' + fmt(y.total) + '</span></button>';
    }).join('');
  }

  /* ---------- rejestry ---------- */

  function renderTabs() {
    if (!state.data) { elTabs.innerHTML = ''; return; }
    elTabs.innerHTML = state.data.registers.map(function (r) {
      return '<button class="tab" type="button" role="tab" data-reg="' + esc(r.id) + '"' +
             ' aria-selected="' + (r.id === state.reg) + '">' + esc(r.short) +
             '<span class="n">' + fmt(r.rows.length) + '</span></button>';
    }).join('');
  }

  function currentRegister() {
    if (!state.data) return null;
    return state.data.registers.filter(function (r) { return r.id === state.reg; })[0] ||
           state.data.registers[0];
  }

  /* ---------- tabela ---------- */

  function renderTable() {
    var reg = currentRegister();
    if (!reg) {
      elTable.innerHTML = '<p class="empty">Brak rejestrów dla tego rocznika.</p>';
      elCount.textContent = '';
      return;
    }

    var q = state.q.trim().toLowerCase();
    var rows = reg.rows;
    if (q) {
      rows = rows.filter(function (row) {
        for (var k in row.c) {
          if (String(row.c[k]).toLowerCase().indexOf(q) !== -1) return true;
        }
        return String(row.d || '').indexOf(q) !== -1;
      });
    }

    elCount.textContent = q
      ? fmt(rows.length) + ' z ' + fmt(reg.rows.length) + ' pozycji'
      : fmt(reg.rows.length) + ' pozycji';

    if (!rows.length) {
      elTable.innerHTML = '<p class="empty">Nic nie pasuje do „' + esc(state.q) + '”.</p>';
      return;
    }

    var head = '<tr><th>Data</th>' + reg.cols.map(function (c) {
      return '<th>' + esc(c.l) + '</th>';
    }).join('') + '</tr>';

    var body = rows.map(function (row) {
      var tds = reg.cols.map(function (c) {
        return '<td class="' + esc(c.w || '') + '">' + esc(row.c[c.k]) + '</td>';
      }).join('');
      return '<tr><td class="nr">' + esc(row.d || '—') + '</td>' + tds + '</tr>';
    }).join('');

    elTable.innerHTML = '<table><thead>' + head + '</thead><tbody>' + body + '</tbody></table>';
  }

  function renderSource() {
    if (!state.data) { elSource.innerHTML = ''; return; }
    var reg = currentRegister();
    var bits = [];
    if (reg && reg.url) {
      bits.push('źródło: <a href="' + esc(reg.url) + '" target="_blank" rel="noopener">' +
                esc(reg.file || 'plik') + '</a>');
    }
    if (reg && reg.desc) bits.push(esc(reg.desc));
    bits.push('wygenerowano ' + esc(state.data.generated.slice(0, 10)));
    elSource.innerHTML = bits.join(' · ');
  }

  /* ---------- ładowanie ---------- */

  function loadYear() {
    elTable.innerHTML = '<p class="empty">Wczytywanie…</p>';
    var url = 'data/' + state.district + '/' + state.year + '.json';
    return getJSON(url).then(function (data) {
      state.data = data;
      var ids = data.registers.map(function (r) { return r.id; });
      if (ids.indexOf(state.reg) === -1) state.reg = ids[0] || null;
      renderTabs();
      renderTable();
      renderSource();
      writeHash();
    }).catch(function (e) {
      state.data = null;
      elTabs.innerHTML = '';
      elTable.innerHTML = '<p class="error">Nie udało się wczytać danych: ' + esc(e.message) + '</p>';
    });
  }

  function selectDistrict(slug) {
    var d = districtEntry(slug);
    if (!d) return;
    state.district = slug;
    state.year = d.default;
    state.reg = null;
    state.data = null;
    elDistrict.value = slug;
    renderYears();
    return loadYear();
  }

  function selectYear(year) {
    state.year = Number(year);
    state.reg = null;
    renderYears();
    return loadYear();
  }

  /* ---------- zdarzenia ---------- */

  elDistrict.addEventListener('change', function () {
    selectDistrict(this.value);
  });

  elYears.addEventListener('click', function (e) {
    var b = e.target.closest('.year');
    if (b) selectYear(b.dataset.year);
  });

  elTabs.addEventListener('click', function (e) {
    var b = e.target.closest('.tab');
    if (!b) return;
    state.reg = b.dataset.reg;
    renderTabs();
    renderTable();
    renderSource();
    writeHash();
  });

  var timer = null;
  elQ.addEventListener('input', function () {
    var v = this.value;
    clearTimeout(timer);
    timer = setTimeout(function () { state.q = v; renderTable(); }, 120);
  });

  window.addEventListener('hashchange', function () {
    var h = readHash();
    if (h.district && h.district !== state.district) {
      selectDistrict(h.district).then(function () {
        if (h.year) selectYear(h.year);
      });
    }
  });

  /* ---------- start ---------- */

  getJSON('data/index.json').then(function (index) {
    state.index = index;
    var h = readHash();
    var withData = index.districts.filter(function (d) { return d.years.length; });
    if (!withData.length) throw new Error('manifest bez danych');

    var start = withData.filter(function (d) { return d.slug === h.district; })[0] ||
                withData.filter(function (d) { return d.slug === 'ursus'; })[0] ||
                withData[0];

    state.district = start.slug;
    state.year = start.default;
    state.reg = h.reg || null;

    renderDistricts();
    renderYears();
    return loadYear().then(function () {
      if (h.year && Number(h.year) !== state.year) return selectYear(h.year);
    });
  }).catch(function (e) {
    elTable.innerHTML = '<p class="error">Nie udało się wczytać manifestu: ' +
                        esc(e.message) + '</p>';
  });
})();
