# Deploy шпаргалка — ШТУРМ

Сейчас всё, что собирает `python -m pygbag --build main.py`, лежит в
`build/web/`. Это ~45 КБ + иконка `icon-256.png`. Ниже — пошаговый план,
чтобы залить на GitHub Pages и подать в VK Mini Apps.

## 1. GitHub Pages

```bash
# в корне репозитория contra-vk:
git init
git add .
git commit -m "shturm v0.7"
git branch -M main
git remote add origin https://github.com/<USERNAME>/shturm.git
git push -u origin main

# создаём ветку gh-pages с содержимым build/web/
git checkout --orphan gh-pages
git rm -rf .
cp -r build/web/* .
# для index.html GitHub Pages поднимет MIME-types корректно
git add .
git commit -m "deploy v0.7"
git push origin gh-pages
git checkout main
```

В **Settings → Pages** репозитория выбрать `Branch: gh-pages` / `(root)`.
Получишь URL вида `https://<username>.github.io/shturm/`.

> **CORS / mime.** Pygbag-сборка тянет Python WASM с
> `pygame-web.github.io/cdn/0.9.3/`, поэтому статике на GitHub Pages
> ничего настраивать не нужно.

## 2. Альтернатива — Vercel

```bash
npm i -g vercel
cd build/web
vercel --prod
```

После `vercel login` получишь URL `https://shturm-<hash>.vercel.app`.

## 3. VK Mini App

1. https://vk.com/editapp?act=create → **Embedded HTML5**.
2. Платформы: «Веб-приложение», размер — «Развернуть на весь экран».
3. **Адрес приложения** — URL из шага 1 (`https://<user>.github.io/shturm/`).
4. **Превью**: `assets/icon-256.png` (256×256, PNG).
5. **Видимость**: «Доступно по прямой ссылке» пока тестируешь.
6. Кнопка «Опубликовать» — модерация 1–7 дней.

### Что проверяет ВК:

- Работает в мобильном webview (Chrome ≥100) — наша сборка работает.
- Нет VK Bridge ошибок в DevTools — у нас всё в try/except, никогда не
  выбрасываем.
- Touch-управление есть — есть (D-pad + JUMP + FIRE + PAUSE).
- Нет упоминания торговых марок — *Contra* нигде, везде ШТУРМ.

### VK Bridge заглушки

`game/vk_bridge.py` уже умеет вызывать:

- `VKWebAppInit` — при старте, чтобы VK перестал показывать спиннер.
- `VKWebAppShare` — заготовка под кнопку «Поделиться рекордом».

На десктопе всё no-op, можешь спокойно разрабатывать локально.

## 4. itch.io (альтернатива на пока VK ревьюит)

Pygbag сразу пакует под itch.io:
```bash
python -m pygbag --build main.py
# выкладываешь build/web/contra-vk.apk как HTML5 на itch.io
```

## 5. Локальная проверка перед деплоем

```bash
python -m pygbag --port 8001 main.py
# открываешь http://localhost:8001/
```

Первая загрузка 10–30 сек (тянется ~10 MB WASM Python из CDN), дальше
кэшируется и стартует за пару секунд.

## 6. Финальный чек-лист

- [ ] `python _smoke_test.py` — зелёный
- [ ] `python -m pygbag --build main.py` — без ошибок
- [ ] `python tools/make_icon.py` — есть `icon-256.png`
- [ ] Тестово открыл `index.html` локально на телефоне (DevTools → Responsive)
- [ ] Перевыкатил на GitHub Pages (`gh-pages` ветка)
- [ ] Создал VK Mini App, указал URL и иконку
- [ ] Подал на модерацию
