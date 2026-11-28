/**
 * Documentation screenshots, captured as a side effect of the E2E run.
 *
 * `docShot()` and the docs rendering in `newContext()` are inert unless
 * `DOCS_SCREENSHOTS=1` is set (see the `test:e2e:docs` script), so screenshots are strictly
 * opt-in. (The extra E2E coverage that exists to reach each documented screen is ordinary
 * test code and runs every time.)
 *
 * - `newContext(browser)` replaces `browser.newContext()` in every spec. In
 *   docs mode it pins a fixed viewport and device scale factor, so output is
 *   the same size regardless of the host machine's display.
 * - `docShot(page, 'folder/name')` writes `docs/images/folder/name.png` via
 *   Playwright's `toHaveScreenshot`. Run with `--update-snapshots=changed` it
 *   only rewrites a file when the pixels differ beyond `MAX_DIFF_PIXEL_RATIO`,
 *   so regenerating does not churn Git.
 *
 * The set of valid names is the set of images referenced from the markdown under `docs/`;
 * `scripts/check-docs-screenshots.mjs` enforces that in both directions.
 */
import {
  expect,
  type Browser,
  type BrowserContext,
  type Locator,
  type Page,
} from '@playwright/test';

export const DOCS_MODE = process.env.DOCS_SCREENSHOTS === '1';

/** 1728x992 CSS pixels at 2x -> 3456x1984 PNGs, the size the existing docs use. */
export const DOCS_VIEWPORT = { width: 1728, height: 992 } as const;
export const DOCS_SCALE = 2;

/**
 * Fraction of pixels allowed to differ before a screenshot is considered changed (~1.4k of
 * 6.9M). Small enough that a changed label or badge rewrites the file; big enough to absorb
 * anti-aliasing noise between runs in the same container.
 */
export const MAX_DIFF_PIXEL_RATIO = 0.0002;

/** Drop-in for `browser.newContext()`; applies the fixed docs rendering in docs mode. */
export async function newContext(browser: Browser): Promise<BrowserContext> {
  if (!DOCS_MODE) return browser.newContext();
  return browser.newContext({
    viewport: DOCS_VIEWPORT,
    deviceScaleFactor: DOCS_SCALE,
    reducedMotion: 'reduce',
    locale: 'en-GB',
    timezoneId: 'Europe/London',
    colorScheme: 'light',
  });
}

export interface DocShotOptions {
  /**
   * Replace the text of elements whose content varies run to run (timestamps, generated
   * passwords, hostnames) with a fixed, realistic value. Preferred over `mask` because the
   * result still reads naturally in the docs. Each locator must match at least one element
   * (a drifted selector fails the test instead of capturing the real value), and the original
   * text must not look broken (`undefined`, `Invalid Date`, ...), so a UI bug isn't papered over.
   * Replaces the whole text (child nodes included) of non-input elements.
   */
  fixText?: Array<{ locator: Locator; text: string }>;
  /** Paint over elements that have no sensible fixed text (a grey box in the docs). */
  mask?: Locator[];
}

/**
 * Capture a documentation screenshot of the current viewport. No-op outside docs mode.
 *
 * @param name Path under `docs/images/` without extension, e.g. `config_show/cast_overview`.
 */
export async function docShot(
  page: Page,
  name: string,
  options: DocShotOptions = {}
): Promise<void> {
  if (!DOCS_MODE) return;
  // Toasts from the preceding action would otherwise be captured mid-animation. Don't move the
  // mouse onto one while waiting: hovering pauses its auto-dismiss timer.
  await expect(page.locator('.v-toast__item')).toHaveCount(0, { timeout: 15_000 });
  // Let web fonts and layout settle; toHaveScreenshot then waits for two identical frames.
  await page.evaluate(() => document.fonts.ready);
  for (const { locator, text } of options.fixText ?? []) {
    await expect(locator, 'fixText selector matched nothing').not.toHaveCount(0);
    const originals = await locator.evaluateAll(
      (els, value) =>
        els.map((el) => {
          const isField = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
          const original = isField ? el.value : (el.textContent ?? '');
          // Object.assign: these are page DOM nodes, deliberately mutated for the screenshot.
          Object.assign(el, isField ? { value } : { textContent: value });
          return original;
        }),
      text
    );
    // Case-sensitive with word boundaries: the replaced values include random passwords, tokens
    // and temp-dir names, which can contain "nan" or "null" inside ordinary text.
    const broken = originals.filter((o) =>
      /\bundefined\b|\bnull\b|\bNaN\b|Invalid Date|\[object /.test(o)
    );
    expect(broken, 'fixText replaced text that looks like a UI bug').toEqual([]);
  }
  for (const locator of options.mask ?? []) {
    await expect(locator, 'mask selector matched nothing').not.toHaveCount(0);
  }
  // Passed as path segments: Playwright sanitises a plain string name (turning `_` and `/` into
  // `-`), but joins an array as-is, which keeps the docs' folder layout and file names.
  await expect(page).toHaveScreenshot(`${name}.png`.split('/'), {
    animations: 'disabled',
    caret: 'hide',
    scale: 'device',
    maxDiffPixelRatio: MAX_DIFF_PIXEL_RATIO,
    mask: options.mask,
    maskColor: '#9ca3af',
  });
}
