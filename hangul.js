/* Korea Plainly: learn to read Hangul. Letter tables with sound, a "read the sign" quiz and a memory game.
   Everything runs in the page; scores are kept in this browser only (if storage is allowed). */
(function () {
  "use strict";

  var CONS = [
    ["ㄱ", "g / k", "가"], ["ㄴ", "n", "나"], ["ㄷ", "d / t", "다"], ["ㄹ", "r / l", "라"], ["ㅁ", "m", "마"],
    ["ㅂ", "b / p", "바"], ["ㅅ", "s", "사"], ["ㅇ", "silent / ng", "아"], ["ㅈ", "j", "자"], ["ㅊ", "ch", "차"],
    ["ㅋ", "k", "카"], ["ㅌ", "t", "타"], ["ㅍ", "p", "파"], ["ㅎ", "h", "하"]
  ];
  var DOUBLE = [["ㄲ", "kk", "까"], ["ㄸ", "tt", "따"], ["ㅃ", "pp", "빠"], ["ㅆ", "ss", "싸"], ["ㅉ", "jj", "짜"]];
  var VOW = [
    ["ㅏ", "a", "아"], ["ㅑ", "ya", "야"], ["ㅓ", "eo", "어"], ["ㅕ", "yeo", "여"], ["ㅗ", "o", "오"],
    ["ㅛ", "yo", "요"], ["ㅜ", "u", "우"], ["ㅠ", "yu", "유"], ["ㅡ", "eu", "으"], ["ㅣ", "i", "이"],
    ["ㅐ", "ae", "애"], ["ㅔ", "e", "에"]
  ];
  // word, romanisation, meaning: things you will actually see on signs and menus
  var WORDS = [
    ["서울", "Seoul", "Seoul"], ["부산", "Busan", "Busan"], ["제주", "Jeju", "Jeju"], ["한국", "Hanguk", "Korea"],
    ["커피", "keopi", "coffee"], ["우유", "uyu", "milk"], ["물", "mul", "water"], ["맥주", "maekju", "beer"],
    ["김밥", "gimbap", "rice rolls"], ["라면", "ramyeon", "instant noodles"], ["비빔밥", "bibimbap", "mixed rice"],
    ["치킨", "chikin", "fried chicken"], ["버스", "beoseu", "bus"], ["택시", "taeksi", "taxi"],
    ["지하철", "jihacheol", "subway"], ["역", "yeok", "station"], ["출구", "chulgu", "exit"], ["입구", "ipgu", "entrance"],
    ["화장실", "hwajangsil", "toilet"], ["호텔", "hotel", "hotel"], ["편의점", "pyeonuijeom", "convenience store"],
    ["시장", "sijang", "market"], ["공항", "gonghang", "airport"], ["병원", "byeongwon", "hospital"]
  ];

  function $(sel, root) { return (root || document).querySelector(sel); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function store(key, val) {
    try { if (val === undefined) return window.localStorage.getItem(key); window.localStorage.setItem(key, val); } catch (e) { return null; }
    return null;
  }

  // ---- sound: the browser's own Korean voice, if it has one
  var koVoice = null;
  function findVoice() {
    if (!("speechSynthesis" in window)) return;
    var v = window.speechSynthesis.getVoices();
    for (var i = 0; i < v.length; i++) if (/^ko/i.test(v[i].lang)) { koVoice = v[i]; break; }
    var note = $("#kh-sound-note");
    if (note && koVoice) note.textContent = "Tap a letter to hear it in a syllable, the way Koreans practise.";
  }
  if ("speechSynthesis" in window) { findVoice(); window.speechSynthesis.onvoiceschanged = findVoice; }
  function say(text) {
    if (!koVoice) return;
    try {
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text); u.lang = "ko-KR"; u.voice = koVoice; u.rate = 0.8;
      window.speechSynthesis.speak(u);
    } catch (e) { /* no sound is fine */ }
  }

  // ---- letter tables
  function table(id, rows) {
    var box = document.getElementById(id); if (!box) return;
    rows.forEach(function (r) {
      var b = el("button", "kh-letter"); b.type = "button";
      b.appendChild(el("span", "kh-big", r[0]));
      b.appendChild(el("span", "kh-rom", r[1]));
      var ex = el("span", "kh-ex", "as in " + r[2]); b.appendChild(ex);
      b.addEventListener("click", function () { say(r[2]); b.classList.add("on"); setTimeout(function () { b.classList.remove("on"); }, 600); });
      box.appendChild(b);
    });
  }
  table("kh-cons", CONS); table("kh-double", DOUBLE); table("kh-vow", VOW);

  // ---- Kkachi says things
  var KK_GOOD = ["Nice one!", "You read that!", "Perfect!", "Korean signs, here you come!", "Great reading!"];
  var KK_BAD = ["Nearly! Look at the vowel again.", "Not quite. Try sounding it out.", "Close! Check the first letter."];
  function kkachi(box, msg, good) {
    if (!box) return;
    box.querySelector("p").textContent = msg;
    box.classList.remove("hop", "shake"); void box.offsetWidth; box.classList.add(good ? "hop" : "shake");
  }

  // ---- quiz: read the sign
  var quiz = $("#kh-quiz");
  if (quiz) {
    var qWord = $(".kh-sign", quiz), qOpts = $(".kh-opts", quiz), qScore = $(".kh-score", quiz), qKk = $(".kh-kkachi", quiz);
    var right = 0, total = 0, streak = 0, order = shuffle(WORDS), qi = 0;
    var next = function () {
      if (qi >= order.length) { order = shuffle(WORDS); qi = 0; }
      var w = order[qi++];
      qWord.textContent = w[0];
      qOpts.innerHTML = "";
      var wrong = shuffle(WORDS.filter(function (x) { return x !== w; })).slice(0, 3);
      shuffle([w].concat(wrong)).forEach(function (o) {
        var b = el("button", "kh-opt", o[1] + " · " + o[2]); b.type = "button";
        b.addEventListener("click", function () {
          if (qOpts.dataset.done) return; qOpts.dataset.done = "1"; total++;
          if (o === w) { right++; streak++; b.classList.add("good"); kkachi(qKk, KK_GOOD[streak % KK_GOOD.length] + (streak > 2 ? " " + streak + " in a row." : ""), true); say(w[0]); }
          else {
            streak = 0; b.classList.add("bad"); kkachi(qKk, KK_BAD[total % KK_BAD.length] + " It says " + w[1] + ".", false);
            Array.prototype.forEach.call(qOpts.children, function (c) { if (c.textContent.indexOf(w[1] + " ·") === 0) c.classList.add("good"); });
          }
          qScore.textContent = right + " / " + total;
          setTimeout(function () { delete qOpts.dataset.done; next(); }, 1400);
        });
        qOpts.appendChild(b);
      });
    };
    next();
  }

  // ---- memory game: turn two cards, match the Hangul with its reading
  var game = $("#kh-memory");
  if (game) {
    var grid = $(".kh-grid", game), info = $(".kh-info", game), gKk = $(".kh-kkachi", game);
    var mode = "letters", first = null, lock = false, moves = 0, found = 0, pairs = 6, t0 = 0, timer = null;
    var best = function () { return store("kh-best-" + mode); };
    var show = function () {
      var sec = t0 ? Math.round((Date.now() - t0) / 1000) : 0;
      info.textContent = "Moves: " + moves + " · Pairs: " + found + "/" + pairs + " · Time: " + sec + "s" + (best() ? " · Best: " + best() + " moves" : "");
    };
    var deal = function () {
      clearInterval(timer); timer = null; t0 = 0; moves = 0; found = 0; first = null; lock = false;
      var src = mode === "letters" ? shuffle(CONS.concat(VOW)).slice(0, pairs).map(function (r) { return [r[0], r[1]]; })
                                   : shuffle(WORDS).slice(0, pairs).map(function (r) { return [r[0], r[2]]; });
      var cards = [];
      src.forEach(function (p, i) { cards.push({ id: i, face: p[0], ko: true }); cards.push({ id: i, face: p[1], ko: false }); });
      grid.innerHTML = "";
      shuffle(cards).forEach(function (c) {
        var b = el("button", "kh-card"); b.type = "button"; b.setAttribute("aria-label", "Hidden card");
        var face = el("span", "kh-face" + (c.ko ? " ko" : ""), c.face); b.appendChild(face);
        b.addEventListener("click", function () { flip(b, c); });
        grid.appendChild(b);
      });
      kkachi(gKk, mode === "letters" ? "Match each letter with its sound." : "Match each word with its meaning.", true);
      show();
    };
    var flip = function (b, c) {
      if (lock || b.classList.contains("up") || b.classList.contains("done")) return;
      if (!t0) { t0 = Date.now(); timer = setInterval(show, 1000); }
      b.classList.add("up"); b.setAttribute("aria-label", c.face);
      if (c.ko) say(c.face);
      if (!first) { first = { b: b, c: c }; return; }
      moves++;
      if (first.c.id === c.id) {
        first.b.classList.add("done"); b.classList.add("done"); found++; first = null;
        if (found === pairs) {
          clearInterval(timer);
          var sec = Math.round((Date.now() - t0) / 1000);
          var prev = parseInt(best() || "0", 10);
          if (!prev || moves < prev) store("kh-best-" + mode, String(moves));
          kkachi(gKk, "All matched in " + moves + " moves and " + sec + " seconds!" + (!prev || moves < prev ? " A new best!" : "") + " Play again?", true);
        } else kkachi(gKk, KK_GOOD[found % KK_GOOD.length], true);
        show();
      } else {
        lock = true; var a = first; first = null;
        setTimeout(function () { a.b.classList.remove("up"); b.classList.remove("up"); a.b.setAttribute("aria-label", "Hidden card"); b.setAttribute("aria-label", "Hidden card"); lock = false; show(); }, 900);
      }
    };
    Array.prototype.forEach.call(game.querySelectorAll("[data-mode]"), function (btn) {
      btn.addEventListener("click", function () {
        mode = btn.getAttribute("data-mode");
        Array.prototype.forEach.call(game.querySelectorAll("[data-mode]"), function (x) { x.classList.toggle("sel", x === btn); });
        deal();
      });
    });
    $(".kh-again", game).addEventListener("click", deal);
    deal();
  }
})();
