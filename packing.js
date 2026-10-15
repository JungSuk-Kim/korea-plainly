/* Korea Plainly packing list: pick a season, tick items off; ticks are kept in this browser (if storage is allowed). */
(function () {
  "use strict";
  var COMMON = {
    "Documents": ["Passport (valid for your whole stay)", "K-ETA or visa, if your passport needs one", "e-Arrival Card done online (or fill one in on the plane)", "Hotel addresses saved, in Korean too", "Travel insurance details", "Flight and train bookings (screenshots)"],
    "Money": ["A Visa or Mastercard that works abroad", "A second card, kept separately", "A little Korean cash for markets and street food", "A transit card (buy one on arrival)"],
    "Phone and tech": ["eSIM, SIM or pocket Wi-Fi booked", "Naver Map or KakaoMap installed", "Papago or another translation app", "Kakao T for taxis", "Power adapter: Korea uses type C/F plugs, 220V", "Power bank (in your cabin bag, not checked in)"],
    "Health": ["Your regular medicines, in original packaging", "A few plasters and painkillers", "Face masks for dusty days", "Hand sanitiser and tissues (some toilets have none)"],
    "Handy extras": ["Comfortable walking shoes", "Socks without holes (you take shoes off in some restaurants and temples)", "A foldable shopping bag (plastic bags cost extra)", "A small towel or handkerchief", "Space for shopping on the way home"]
  };
  var SEASON = {
    spring: { name: "Spring (March to May)", items: ["Light layers: T-shirts and a thin jumper", "A light jacket or trench coat", "A warmer layer for March and chilly evenings", "Sunglasses", "Face masks for yellow dust days", "Allergy tablets if you get hay fever"] },
    summer: { name: "Summer (June to August)", items: ["Light, breathable clothes", "A compact umbrella or rain jacket (monsoon season)", "Sandals or quick-drying shoes", "Sun cream and a hat", "Insect repellent", "A thin layer for cold air-conditioning", "Swimwear for beaches or spas"] },
    autumn: { name: "Autumn (September to November)", items: ["Layers: T-shirts plus a jumper or fleece", "A light jacket, and a warm coat for November", "Comfortable shoes for hikes to see the leaves", "Sunglasses", "Lip balm (the air gets dry)"] },
    winter: { name: "Winter (December to February)", items: ["A warm padded coat", "Thermal underwear", "Hat, gloves and a scarf", "Warm, waterproof shoes with grip", "Moisturiser and lip balm", "Heat packs (or buy them at convenience stores)", "Thin layers to take off indoors"] }
  };
  var root = document.getElementById("kp-pack"); if (!root) return;
  var tabs = root.querySelector(".pk-tabs"), list = root.querySelector(".pk-list"), count = root.querySelector(".pk-count");
  var month = new Date().getMonth(), season = month < 2 || month === 11 ? "winter" : month < 5 ? "spring" : month < 8 ? "summer" : "autumn";
  try { season = localStorage.getItem("pk-season") || season; } catch (e) {}
  function key() { return "pk-done-" + season; }
  function done() { try { return JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { return memo[key()] || {}; } }
  var memo = {};
  function save(d) { memo[key()] = d; try { localStorage.setItem(key(), JSON.stringify(d)); } catch (e) {} }
  function render() {
    tabs.innerHTML = "";
    Object.keys(SEASON).forEach(function (s) {
      var b = document.createElement("button"); b.type = "button"; b.textContent = SEASON[s].name.split(" (")[0];
      if (s === season) b.className = "sel";
      b.addEventListener("click", function () { season = s; try { localStorage.setItem("pk-season", s); } catch (e) {} render(); });
      tabs.appendChild(b);
    });
    var groups = {}, nm = SEASON[season].name; groups["Clothes for " + nm.charAt(0).toLowerCase() + nm.slice(1)] = SEASON[season].items;
    Object.keys(COMMON).forEach(function (g) { groups[g] = COMMON[g]; });
    var d = done(), n = 0, all = 0;
    list.innerHTML = "";
    Object.keys(groups).forEach(function (g) {
      var h = document.createElement("h3"); h.textContent = g.charAt(0).toUpperCase() + g.slice(1); list.appendChild(h);
      var ul = document.createElement("ul");
      groups[g].forEach(function (item) {
        all++; if (d[item]) n++;
        var li = document.createElement("li"), lab = document.createElement("label"), cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = !!d[item];
        cb.addEventListener("change", function () { var x = done(); if (cb.checked) x[item] = 1; else delete x[item]; save(x); render(); });
        lab.appendChild(cb); lab.appendChild(document.createTextNode(" " + item)); li.appendChild(lab); ul.appendChild(li);
      });
      list.appendChild(ul);
    });
    count.textContent = n + " of " + all + " packed" + (n === all ? ". You're ready, have a wonderful trip!" : "");
    root.querySelector(".pk-bar i").style.width = Math.round(100 * n / all) + "%";
  }
  root.querySelector(".pk-print").addEventListener("click", function () { window.print(); });
  root.querySelector(".pk-reset").addEventListener("click", function () { save({}); render(); });
  render();
})();
