# builds kkachi_<state>.svg for states: closed, open, blink
BASE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 560" width="520" height="560">
 <!-- long magpie tail -->
 <path d="M150 360 Q60 380 8 470 Q24 478 40 470 Q100 420 170 400 Z" fill="#17243C"/>
 <path d="M30 462 Q90 410 160 388" stroke="#3E6FB0" stroke-width="9" fill="none" stroke-linecap="round"/>
 <!-- feet -->
 <path d="M238 470 v34 M222 504 h32 M292 470 v34 M276 504 h32" stroke="#17243C" stroke-width="10" stroke-linecap="round"/>
 <!-- body: slimmer, upright -->
 <path d="M260 160 C350 160 380 250 372 330 C364 420 320 478 262 478 C200 478 162 420 160 340 C158 260 180 160 260 160 Z" fill="#17243C"/>
 <!-- white belly -->
 <path d="M262 270 C320 270 345 330 340 385 C334 440 300 466 264 466 C226 466 198 440 196 392 C194 330 212 270 262 270 Z" fill="#F7F6F1"/>
 <!-- wing with white shoulder patch and blue sheen -->
 <path d="M175 250 C140 300 150 380 205 420 C232 360 228 290 200 250 Z" fill="#203253"/>
 <path d="M180 262 C168 290 172 318 186 336 C200 312 202 284 192 262 Z" fill="#F7F6F1"/>
 <path d="M168 352 Q178 392 204 412" stroke="#3E6FB0" stroke-width="8" fill="none" stroke-linecap="round"/>
 <!-- red scarf -->
 <path d="M178 238 Q262 282 350 236 L354 262 Q262 310 176 264 Z" fill="#C9413A"/>
 <path d="M318 258 L350 336 L306 322 Z" fill="#C9413A"/>
 <path d="M318 258 L336 300" stroke="#A7302A" stroke-width="5"/>
 <!-- head -->
 <circle cx="262" cy="150" r="98" fill="#17243C"/>
 <path d="M200 92 Q230 60 270 60" stroke="#2A4170" stroke-width="10" fill="none" stroke-linecap="round" opacity=".7"/>
 {EYES}
 <ellipse cx="196" cy="196" rx="17" ry="9" fill="#F2A7A0" opacity=".9"/>
 <ellipse cx="330" cy="196" rx="17" ry="9" fill="#F2A7A0" opacity=".9"/>
 {BEAK}
 <!-- map -->
 <g transform="translate(340 330) rotate(10)">
  <rect width="100" height="74" rx="7" fill="#fff" stroke="#17243C" stroke-width="7"/>
  <path d="M34 0 V74 M67 0 V74" stroke="#17243C" stroke-width="3" opacity=".35"/>
  <path d="M12 56 Q44 22 86 32" stroke="#C9413A" stroke-width="6" fill="none" stroke-dasharray="9 7"/>
  <circle cx="86" cy="32" r="8" fill="#C9413A"/>
 </g>
</svg>'''
EYES_OPEN = '''<circle cx="226" cy="146" r="26" fill="#fff"/><circle cx="232" cy="149" r="14" fill="#17243C"/><circle cx="237" cy="142" r="5" fill="#fff"/>
 <circle cx="300" cy="146" r="26" fill="#fff"/><circle cx="306" cy="149" r="14" fill="#17243C"/><circle cx="311" cy="142" r="5" fill="#fff"/>'''
EYES_BLINK = '''<path d="M204 150 Q226 162 248 150" stroke="#fff" stroke-width="8" fill="none" stroke-linecap="round"/>
 <path d="M278 150 Q300 162 322 150" stroke="#fff" stroke-width="8" fill="none" stroke-linecap="round"/>'''
BEAK_CLOSED = '''<path d="M246 178 L312 190 L250 206 Z" fill="#E8A33D" stroke="#17243C" stroke-width="5" stroke-linejoin="round"/>'''
BEAK_OPEN = '''<path d="M244 176 L304 186 L300 214 L250 214 Z" fill="#7A2420" stroke="#17243C" stroke-width="5" stroke-linejoin="round"/>
 <path d="M244 172 L314 184 L248 194 Z" fill="#E8A33D" stroke="#17243C" stroke-width="5" stroke-linejoin="round"/>
 <path d="M248 206 L300 210 L252 226 Z" fill="#D88A22" stroke="#17243C" stroke-width="5" stroke-linejoin="round"/>'''
import sys
out = sys.argv[1]
for name, eyes, beak in (("closed", EYES_OPEN, BEAK_CLOSED), ("open", EYES_OPEN, BEAK_OPEN), ("blink", EYES_BLINK, BEAK_CLOSED)):
    open(f"{out}/kkachi_{name}.svg", "w").write(BASE.replace("{EYES}", eyes).replace("{BEAK}", beak))
