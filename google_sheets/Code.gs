/**
 * 뚱힐러/뚱헌터 라이선스 구글시트 — Apps Script
 *
 * 시트 열: A=코드, B=HWID, C=기간, D=만료일
 *   C = 숫자(일수) 또는 YYYY-MM-DD(만료일) 또는 0(즉시만료)
 *   D = 끝나는 날짜 YYYY-MM-DD (C가 숫자일 때 실제 만료일)
 *
 * 설치:
 * 1. 구글시트 → 확장 프로그램 → Apps Script
 * 2. 이 파일 전체 붙여넣기 (기존 doPost 포함)
 * 3. 저장 후 시트 새로고침 → 상단 "뚱힐러 관리" 메뉴
 */

var TZ = 'Asia/Seoul';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('뚱힐러 관리')
    .addItem('만료일에서 일수 추가…', 'openExtendSidebar')
    .addSeparator()
    .addItem('선택 행 +7일 (만료일 기준)', 'menuExtend7')
    .addItem('선택 행 +30일 (만료일 기준)', 'menuExtend30')
    .addItem('선택 행 +90일 (만료일 기준)', 'menuExtend90')
    .addToUi();
}

function openExtendSidebar() {
  var html = HtmlService.createHtmlOutput(getExtendSidebarHtml_())
    .setTitle('만료일 연장')
    .setWidth(300);
  SpreadsheetApp.getUi().showSidebar(html);
}

function menuExtend7() { extendSelectedRows_(7); }
function menuExtend30() { extendSelectedRows_(30); }
function menuExtend90() { extendSelectedRows_(90); }

/** 사이드바: 선택 행 미리보기 */
function getExtendPreview() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var row = sheet.getActiveRange() ? sheet.getActiveRange().getRow() : 0;
  if (row < 2) {
    return { ok: false, msg: '코드 행을 선택하세요.' };
  }
  var code = String(sheet.getRange(row, 1).getValue() || '').trim();
  if (!code) {
    return { ok: false, msg: '선택한 행에 코드가 없습니다.' };
  }
  var info = readExpireInfo_(sheet, row);
  return {
    ok: true,
    row: row,
    code: code,
    currentEnd: info.currentEndStr,
    daysLabel: info.daysLabel,
    expired: info.expired
  };
}

/** 사이드바: 적용 */
function applyExtendFromSidebar(addDays) {
  addDays = parseInt(addDays, 10);
  if (!addDays || addDays < 1) {
    return { ok: false, msg: '1 이상의 숫자를 입력하세요.' };
  }
  var sheet = SpreadsheetApp.getActiveSheet();
  var row = sheet.getActiveRange() ? sheet.getActiveRange().getRow() : 0;
  if (row < 2) {
    return { ok: false, msg: '코드 행을 선택하세요.' };
  }
  var code = String(sheet.getRange(row, 1).getValue() || '').trim();
  if (!code) {
    return { ok: false, msg: '선택한 행에 코드가 없습니다.' };
  }
  var before = readExpireInfo_(sheet, row);
  var result = extendRow_(sheet, row, addDays);
  var after = readExpireInfo_(sheet, row);
  return {
    ok: true,
    code: code,
    beforeEnd: before.currentEndStr,
    afterEnd: after.currentEndStr,
    detail: result
  };
}

function extendSelectedRows_(addDays) {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getActiveRange();
  if (!range) {
    SpreadsheetApp.getUi().alert('연장할 행을 선택하세요.');
    return;
  }
  var startRow = range.getRow();
  var endRow = range.getLastRow();
  if (startRow < 2) startRow = 2;

  var logs = [];
  for (var row = startRow; row <= endRow; row++) {
    var code = String(sheet.getRange(row, 1).getValue() || '').trim();
    if (!code) continue;
    var before = readExpireInfo_(sheet, row);
    var result = extendRow_(sheet, row, addDays);
    var after = readExpireInfo_(sheet, row);
    logs.push(code + '\n  ' + before.currentEndStr + ' → ' + after.currentEndStr);
  }

  if (logs.length === 0) {
    SpreadsheetApp.getUi().alert('처리할 코드가 없습니다. (1행은 헤더)');
    return;
  }
  SpreadsheetApp.getUi().alert('만료일에서 +' + addDays + '일 완료\n\n' + logs.join('\n\n'));
}

/** 현재 만료일 읽기 (표시용) */
function readExpireInfo_(sheet, row) {
  var cRaw = sheet.getRange(row, 3).getValue();
  var dRaw = sheet.getRange(row, 4).getValue();
  var today = startOfDay_(new Date());
  var end = null;
  var daysLabel = '';

  if (cRaw === 0 || cRaw === '0') {
    return { currentEndStr: '(만료됨)', daysLabel: '0일', expired: true, end: null };
  }
  if (isDayCount_(cRaw)) {
    daysLabel = String(parseInt(String(cRaw).trim(), 10)) + '일';
    end = parseDate_(dRaw);
  } else {
    end = parseDate_(cRaw);
    daysLabel = end ? fmtDate_(end) + ' 만료' : '(날짜 없음)';
  }

  if (!end) {
    return { currentEndStr: '(D열 만료일 없음)', daysLabel: daysLabel, expired: false, end: null };
  }
  return {
    currentEndStr: fmtDate_(end),
    daysLabel: daysLabel,
    expired: end < today,
    end: end
  };
}

/**
 * 만료일(D)에서 addDays 더하기.
 * - C 숫자 + D 만료일: D에 +N, C도 +N
 * - C 날짜: C에 +N
 * - 이미 만료: 오늘부터 +N (D/C 새로 설정)
 */
function extendRow_(sheet, row, addDays) {
  var cCell = sheet.getRange(row, 3);
  var dCell = sheet.getRange(row, 4);
  var cRaw = cCell.getValue();
  var dRaw = dCell.getValue();
  var today = startOfDay_(new Date());

  if (cRaw === 0 || cRaw === '0') {
    var end0 = addDays_(today, addDays);
    cCell.setValue(addDays);
    dCell.setValue(fmtDate_(end0));
    return fmtDate_(end0) + '까지';
  }

  if (isDayCount_(cRaw)) {
    var days = parseInt(String(cRaw).trim(), 10);
    var end = parseDate_(dRaw);
    if (end) {
      var base = end < today ? today : end;
      var newEnd = addDays_(base, addDays);
      cCell.setValue(days + addDays);
      dCell.setValue(fmtDate_(newEnd));
      return fmtDate_(end) + ' → ' + fmtDate_(newEnd);
    }
    var newDays = days + addDays;
    var newEnd2 = addDays_(today, newDays);
    cCell.setValue(newDays);
    dCell.setValue(fmtDate_(newEnd2));
    return fmtDate_(newEnd2) + '까지';
  }

  var expire = parseDate_(cRaw);
  if (!expire) {
    return 'C열 형식 오류';
  }
  var base = expire < today ? today : expire;
  var newExpire = addDays_(base, addDays);
  cCell.setValue(fmtDate_(newExpire));
  return fmtDate_(expire) + ' → ' + fmtDate_(newExpire);
}

function isDayCount_(v) {
  if (typeof v === 'number' && v > 0 && v === Math.floor(v)) return true;
  return /^\d+$/.test(String(v).trim());
}

function parseDate_(v) {
  if (!v && v !== 0) return null;
  if (v instanceof Date) return startOfDay_(v);
  var s = String(v).trim();
  var m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return null;
}

function fmtDate_(d) {
  return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
}

function startOfDay_(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function addDays_(d, n) {
  var r = new Date(d.getTime());
  r.setDate(r.getDate() + n);
  return startOfDay_(r);
}

function getExtendSidebarHtml_() {
  return '<!DOCTYPE html><html><head><base target="_top">' +
    '<style>' +
    'body{font-family:Arial,sans-serif;padding:12px;font-size:13px;color:#222;}' +
    'h3{margin:0 0 12px;font-size:15px;}' +
    '.box{background:#f5f5f5;border-radius:8px;padding:10px;margin-bottom:12px;line-height:1.6;}' +
    '.lbl{color:#666;font-size:11px;}' +
    'input{width:100%;box-sizing:border-box;padding:8px;font-size:14px;margin:6px 0 10px;}' +
    '.btns{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;}' +
    '.btn{flex:1;min-width:60px;padding:8px;border:none;border-radius:6px;background:#4285f4;color:#fff;cursor:pointer;font-size:12px;}' +
    '.btn:hover{background:#3367d6;}' +
    '.apply{width:100%;padding:10px;border:none;border-radius:6px;background:#34a853;color:#fff;font-size:14px;font-weight:bold;cursor:pointer;}' +
    '.apply:hover{background:#2d8e47;}' +
    '#preview{color:#1a73e8;font-weight:bold;margin:8px 0;min-height:20px;}' +
    '#msg{color:#d93025;font-size:12px;}' +
    '</style></head><body>' +
    '<h3>만료일에서 일수 추가</h3>' +
    '<div class="box" id="info">행을 선택하세요</div>' +
    '<div class="lbl">추가할 일수</div>' +
    '<input type="number" id="days" value="30" min="1">' +
    '<div class="btns">' +
    '<button class="btn" onclick="setDays(7)">+7</button>' +
    '<button class="btn" onclick="setDays(30)">+30</button>' +
    '<button class="btn" onclick="setDays(90)">+90</button>' +
    '</div>' +
    '<div id="preview"></div>' +
    '<button class="apply" onclick="doApply()">만료일에 추가 적용</button>' +
    '<div id="msg"></div>' +
    '<script>' +
    'var curEnd=null, curExpired=false;' +
    'function setDays(n){document.getElementById("days").value=n;updatePreview();}' +
    'function updatePreview(){' +
    '  var n=parseInt(document.getElementById("days").value,10);' +
    '  var p=document.getElementById("preview");' +
    '  if(!curEnd||!n||n<1){p.textContent="";return;}' +
    '  google.script.run.withSuccessHandler(function(r){' +
    '    if(r&&r.ok)p.textContent=r.preview;' +
    '  }).calcPreview(curEnd, curExpired, n);' +
    '}' +
    'function load(){' +
    '  google.script.run.withSuccessHandler(function(r){' +
    '    var el=document.getElementById("info");' +
    '    if(!r.ok){el.textContent=r.msg;curEnd=null;return;}' +
    '    curEnd=r.currentEnd;curExpired=r.expired;' +
    '    el.innerHTML="<b>"+r.code+"</b><br>현재 만료일: <b>"+r.currentEnd+"</b><br>C열: "+r.daysLabel+(r.expired?" <span style=\\"color:#d93025\\">(만료됨)</span>":"");' +
    '    updatePreview();' +
    '  }).getExtendPreview();' +
    '}' +
    'function doApply(){' +
    '  var n=document.getElementById("days").value;' +
    '  document.getElementById("msg").textContent="처리중...";' +
    '  google.script.run.withSuccessHandler(function(r){' +
    '    if(!r.ok){document.getElementById("msg").textContent=r.msg;return;}' +
    '    document.getElementById("msg").textContent="완료: "+r.beforeEnd+" → "+r.afterEnd;' +
    '    load();' +
    '  }).withFailureHandler(function(e){document.getElementById("msg").textContent=e.message;})' +
    '  .applyExtendFromSidebar(n);' +
    '}' +
    'document.getElementById("days").addEventListener("input",updatePreview);' +
    'load();' +
    '</script></body></html>';
}

/** 사이드바 미리보기: 만료일 + N일 */
function calcPreview(currentEndStr, expired, addDays) {
  addDays = parseInt(addDays, 10);
  var end = parseDate_(currentEndStr);
  if (!end || !addDays) return { ok: false };
  var today = startOfDay_(new Date());
  var base = (expired || end < today) ? today : end;
  var newEnd = addDays_(base, addDays);
  return {
    ok: true,
    preview: currentEndStr + ' 에서 +' + addDays + '일 → ' + fmtDate_(newEnd)
  };
}

// ── HWID 등록 (앱 GAS_API_URL) ─────────────────────────────────────────────

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var code = String(data.code || '').trim();
    var hwid = String(data.hwid || '').trim();
    if (!code || !hwid) {
      return json_({ result: 'FAIL', msg: 'missing code/hwid' });
    }
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
    var rows = sheet.getDataRange().getValues();
    for (var i = 1; i < rows.length; i++) {
      if (String(rows[i][0]).trim() !== code) continue;
      var curHwid = String(rows[i][1] || '').trim();
      if (!curHwid) {
        sheet.getRange(i + 1, 2).setValue(hwid);
        return json_({ result: 'OK' });
      }
      return json_({ result: 'FAIL', msg: 'already registered' });
    }
    return json_({ result: 'NOT_FOUND' });
  } catch (err) {
    return json_({ result: 'ERROR', msg: String(err) });
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
