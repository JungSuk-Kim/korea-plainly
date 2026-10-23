/* Korea Plainly tax refund calculator: a rough estimate of the VAT refund a visitor gets back per receipt.
   Korean prices include 10% VAT (1/11 of the price). Refund operators keep a fee, so visitors usually get back
   about 3% to 8% of the price, a little more on bigger receipts. The operator's own receipt decides. */
(function () {
  "use strict";
  var root = document.getElementById("kp-taxrefund"); if (!root) return;
  var MIN = 15000;            // minimum spend per receipt (one shop, one transaction)
  var INSTANT_MAX = 1000000;  // instant refunds at the shop: purchases under 1 million won each
  var INSTANT_TRIP = 5000000; // ... and 5 million won of instant-refund purchases per trip
  var CUSTOMS = 75000;        // roughly this much refund on one receipt and customs must see the goods
  // [from won, low %, high %] of the price paid, approximate
  var BANDS = [[15000, 3.3, 5], [30000, 5, 6.7], [100000, 6, 7], [300000, 6.5, 7.5], [1000000, 7, 8.2]];
  var MAX_ROWS = 10;
  function f(id) { return root.querySelector("#" + id); }
  function won(n) { return (Math.round(n / 100) * 100).toLocaleString("en-GB") + " won"; }
  function band(a) { var b = null; BANDS.forEach(function (x) { if (a >= x[0]) b = x; }); return b; }
  function amounts() {
    return Array.prototype.map.call(root.querySelectorAll(".tr-amt"), function (i) {
      return Math.max(0, parseInt(String(i.value).replace(/[^0-9]/g, ""), 10) || 0);
    });
  }
  function addRow(v) {
    var list = f("tr-list"), n = list.children.length + 1;
    if (n > MAX_ROWS) return;
    var lab = document.createElement("label");
    lab.innerHTML = "Receipt " + n + " (won) <input class='tr-amt' type='number' min='0' step='1000' inputmode='numeric'>";
    lab.querySelector("input").value = v || "";
    lab.querySelector("input").addEventListener("input", calc);
    list.appendChild(lab);
    f("tr-add").hidden = n >= MAX_ROWS;
  }
  function calc() {
    var instant = f("tr-way").value === "instant";
    var rows = "", lo = 0, hi = 0, notes = [], instantSum = 0, any = false;
    amounts().forEach(function (a, i) {
      if (!a) return;
      any = true;
      var b = band(a), name = "Receipt " + (i + 1) + " (" + won(a) + ")";
      if (!b) { rows += "<tr><td>" + name + "</td><td>Below the 15,000-won minimum</td></tr>"; return; }
      var l = a * b[1] / 100, h = a * b[2] / 100;
      lo += l; hi += h;
      var cell = won(l) + " to " + won(h);
      if (instant) {
        if (a >= INSTANT_MAX) { cell += "<br><small>1 million won or more: claim at the airport, not at the till</small>"; }
        else { instantSum += a; }
      }
      if (h >= CUSTOMS) { cell += "<br><small>Large refund: show the goods to customs before checking in your bags</small>"; }
      rows += "<tr><td>" + name + "</td><td>" + cell + "</td></tr>";
    });
    var out = f("tr-out");
    if (!any) { out.innerHTML = "<p class='bg-day'>Enter the amount on each receipt to see an estimate.</p>"; return; }
    var html = "<table>" + rows;
    if (hi > 0) html += "<tr class='tot'><td>Estimated refund</td><td>" + won(lo) + " to " + won(hi) + "</td></tr>";
    html += "</table>";
    if (instant && instantSum > INSTANT_TRIP) notes.push("Instant refunds stop at 5 million won of purchases per trip; claim the rest at the airport.");
    if (instant) notes.push("At the till the refund comes off the price, so you simply pay less. Bring your physical passport.");
    else notes.push("At an airport kiosk or downtown refund counter, the refund goes to your card or is paid in cash, depending on the operator.");
    notes.push("This is an estimate. The shop or refund operator's receipt shows the exact amount.");
    html += notes.map(function (t) { return "<p class='bg-day'>" + t + "</p>"; }).join("");
    out.innerHTML = html;
  }
  f("tr-add").addEventListener("click", function () { addRow(""); var a = root.querySelectorAll(".tr-amt"); a[a.length - 1].focus(); });
  f("tr-way").addEventListener("change", calc);
  addRow("50000"); addRow("");
  calc();
})();
