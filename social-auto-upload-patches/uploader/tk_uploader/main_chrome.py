# -*- coding: utf-8 -*-
import json
import re
import time
import unicodedata
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from uploader.tk_uploader.tk_config import Tk_Locator
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tiktok_logger


def chuan_caption(x):
    """Bo khoang trang + chuan hoa Unicode + chu thuong: TikTok doi xuong dong thanh dau cach nen so tho se lech."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", x or "")).casefold()


def khop_caption(caption, desc, so_ky_tu=40):
    """Caption cua minh va 'desc' TikTok tra ve co phai cung 1 bai: trung 40 ky tu dau (caption ngan hon thi trung het)."""
    a, b = chuan_caption(caption), chuan_caption(desc)
    k = min(len(a), so_ky_tu)
    return k > 0 and len(b) >= k and a[:k] == b[:k]


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=en")
        await page.wait_for_load_state('networkidle')
        try:
            # 选择所有的 select 元素
            select_elements = await page.query_selector_all('select')
            for element in select_elements:
                class_name = await element.get_attribute('class')
                # 使用正则表达式匹配特定模式的 class 名称
                if re.match(r'tiktok-.*-SelectFormContainer.*', class_name):
                    tiktok_logger.error("[+] cookie expired")
                    return False
            tiktok_logger.success("[+] cookie valid")
            return True
        except:
            tiktok_logger.success("[+] cookie valid")
            return True


async def tiktok_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tk_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        tiktok_logger.info('[+] cookie file is not existed or expired. Now open the browser auto. Please login with your way(gmail phone, whatever, the cookie file will generated after login')
        await get_tiktok_cookie(account_file)
    return True


async def get_tiktok_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB',
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://www.tiktok.com/login?lang=en")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class TiktokVideo(object):
    def __init__(self, title, file_path, tags, publish_date, account_file, thumbnail_path=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.thumbnail_path = thumbnail_path
        self.account_file = account_file
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.locator_base = None
        # --- kiem tra that (15/11/2026): dung tai khoan + thay bai trong danh sach Posts moi tinh la da dang
        self.expected_username = None   # ten @ TikTok phai dung (lay tu cau-hinh.json "username")
        self.account_username = None    # ten @ TikTok that cua file dang nhap
        self.video_id = None            # id bai da duoc TikTok xac nhan
        self.da_co_san = False          # True = bai da co tren TikTok tu truoc, khong dang lai
        self._items = {}                # item_id -> item (tu API item_list cua TikTok Studio)
        self._so_lan_ds = 0
        self.chi_kiem = False           # True = chi kiem bai da len chua (da bam Post o luot truoc), KHONG tai len
        self.khong_bam_post = False     # True = chay thu: tai video + caption len trang Upload roi DUNG truoc nut Post
        self.khi_bam_post = None        # ham goi 1 lan ngay truoc khi bam Post (may dang ghi dau 'da bam')
        self.thu = {}                   # ket qua chay thu (khong_bam_post)
        self.tu_luc = None              # gio may (unix) bat dau thu dang video nay lan dau; bai tao truoc do khong tinh
        self._ids_truoc = None          # id cac bai da co TRUOC khi tai video len (de biet bai nao la moi)
        self._luc_chup = None           # gio may luc chup danh sach tren
        self._lech = 0.0                # dong ho TikTok - dong ho may (giay)
        self.bai_trung = []             # sau khi dang ma thay >1 bai moi cung caption (de bao chu may xoa bot)

    async def set_schedule_time(self, page, publish_date):
        schedule_input_element = self.locator_base.get_by_label('Schedule')
        await schedule_input_element.wait_for(state='visible')  # 确保按钮可见

        await schedule_input_element.click(force=True)
        if await self.locator_base.locator('div.TUXButton-content >> text=Allow').count():
            await self.locator_base.locator('div.TUXButton-content >> text=Allow').click()

        scheduled_picker = self.locator_base.locator('div.scheduled-picker')
        await scheduled_picker.locator('div.TUXInputBox').nth(1).click()

        calendar_month = await self.locator_base.locator(
            'div.calendar-wrapper span.month-title').inner_text()

        n_calendar_month = datetime.strptime(calendar_month, '%B').month

        schedule_month = publish_date.month

        if n_calendar_month != schedule_month:
            if n_calendar_month < schedule_month:
                arrow = self.locator_base.locator('div.calendar-wrapper span.arrow').nth(-1)
            else:
                arrow = self.locator_base.locator('div.calendar-wrapper span.arrow').nth(0)
            await arrow.click()

        # day set
        valid_days_locator = self.locator_base.locator(
            'div.calendar-wrapper span.day.valid')
        valid_days = await valid_days_locator.count()
        for i in range(valid_days):
            day_element = valid_days_locator.nth(i)
            text = await day_element.inner_text()
            if text.strip() == str(publish_date.day):
                await day_element.click()
                break
        # time set
        await scheduled_picker.locator('div.TUXInputBox').nth(0).click()

        hour_str = publish_date.strftime("%H")
        correct_minute = int(publish_date.minute / 5)
        minute_str = f"{correct_minute:02d}"

        hour_selector = f"span.tiktok-timepicker-left:has-text('{hour_str}')"
        minute_selector = f"span.tiktok-timepicker-right:has-text('{minute_str}')"

        # pick hour first
        await page.wait_for_timeout(1000)  # 等待500毫秒
        await self.locator_base.locator(hour_selector).click()
        # click time button again
        await page.wait_for_timeout(1000)  # 等待500毫秒
        # pick minutes after
        await self.locator_base.locator(minute_selector).click()

        # click title to remove the focus.
        # await self.locator_base.locator("h1:has-text('Upload video')").click()

    async def handle_upload_error(self, page):
        tiktok_logger.info("video upload error retrying.")
        select_file_button = self.locator_base.locator('button[aria-label="Select file"]')
        async with page.expect_file_chooser() as fc_info:
            await select_file_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
        context = await browser.new_context(storage_state=f"{self.account_file}")
        # context = await set_init_script(context)
        page = await context.new_page()
        await page.add_init_script("""(() => {
  const st = () => { const s = document.createElement('style'); s.textContent = '#react-joyride-portal,.react-joyride__overlay,.react-joyride__spotlight,.__floater{display:none!important;pointer-events:none!important}'; (document.head||document.documentElement).appendChild(s); };
  document.addEventListener('DOMContentLoaded', st); st();
})();""")  # an huong dan TikTok (joyride) che nut bam

        # change language to eng first
        page.on("response", self._nghe_ds_bai)
        await self.change_language(page)
        await self.kiem_tai_khoan(page)          # sai tai khoan / het han -> dung ngay, KHONG dang
        # da dang roi (luot truoc bam Post xong nhung chua kip xac nhan) -> khong dang trung
        if not await self.tai_ds_bai(page) and not await self.tai_ds_bai(page):
            raise RuntimeError("KHONG_DOC_DUOC_DS_BAI: khong doc duoc danh sach Posts cua TikTok Studio nen khong dang (tranh dang trung)")
        self._ids_truoc, self._luc_chup = set(self._items), time.time()
        co_san = self.tim_bai()
        if co_san:
            self.video_id, self.da_co_san = co_san, True
            tiktok_logger.success(f"  [-] bai nay da co tren TikTok (khong dang lai)")
            tiktok_logger.success(f"video_id: {co_san}")
            await context.close()
            await browser.close()
            return
        if self.chi_kiem:
            await context.close()
            await browser.close()
            raise RuntimeError("CHUA_THAY_BAI: da bam Post o luot truoc, TikTok van chua hien bai (khong tai len lai)")
        await page.goto("https://www.tiktok.com/tiktokstudio/upload")
        tiktok_logger.info(f'[+]Uploading-------{self.title}.mp4')

        await page.wait_for_url("https://www.tiktok.com/tiktokstudio/upload", timeout=10000)

        try:
            await page.wait_for_selector('iframe[data-tt="Upload_index_iframe"], div.upload-container', timeout=10000)
            tiktok_logger.info("Either iframe or div appeared.")
        except Exception as e:
            tiktok_logger.error("Neither iframe nor div appeared within the timeout.")

        await self.choose_base_locator(page)

        upload_button = self.locator_base.locator(
            'button:has-text("Select video"):visible')
        await upload_button.wait_for(state='visible')  # 确保按钮可见

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

        await self.add_title_tags(page)
        # detect upload status
        await self.detect_upload_status(page)
        if self.thumbnail_path:
            tiktok_logger.info(f'[+] Uploading thumbnail file {self.title}.png')
            await self.upload_thumbnails(page)

        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        if self.khong_bam_post:
            nut = await self.nut_post()
            self.thu["toi_nut_post"] = nut is not None
            if nut is not None:
                self.thu["chu_tren_nut"] = (await nut.inner_text(timeout=3000)).strip()[:40]
                self.thu["nut_bi_khoa"] = await nut.get_attribute("disabled") is not None
            tiktok_logger.info(f"  [-] CHAY THU: dung truoc nut Post, khong dang ({self.thu})")
            await context.close()
            await browser.close()
            return
        await self.click_publish(page)
        try:
            await context.storage_state(path=f"{self.account_file}")  # luu dang nhap truoc khi xac nhan
        except Exception:
            pass
        vid = await self.xac_nhan_bai(page)
        if not vid:
            raise RuntimeError("KHONG_XAC_NHAN: da bam Post nhung sau 3 phut khong thay bai moi trong danh sach Posts cua TikTok")
        self.video_id = vid
        tiktok_logger.success(f"video_id: {vid}")
        if self.bai_trung:
            tiktok_logger.warning("bai_trung: " + ",".join(self.bai_trung))

        await context.storage_state(path=f"{self.account_file}")  # save cookie
        tiktok_logger.info('  [-] update cookie！')
        await asyncio.sleep(2)  # close delay for look the video status
        # close all
        await context.close()
        await browser.close()

    # 17/11/2026: dan ca caption bang insert_text thi TikTok chi nhan hashtag CUOI (cac tag truoc thanh chu thuong).
    # Cach dung: dan phan chu, con moi hashtag thi go tung chu -> cho bang goi y -> chon dung muc '#ten' (Enter).
    TOI_DA_HASHTAG = 5   # TikTok chi cho toi da 5 hashtag moi bai; tag thu 6 tro di bi bo
    RE_HASHTAG = re.compile(r"(?<!\S)#([^\s#]+)")

    @staticmethod
    def _k(x):
        return unicodedata.normalize("NFKC", x or "").casefold()

    def tach_caption(self):
        """Caption -> cac doan theo thu tu: ['chu', text] | ['tag', ten]. Bo tag trung va tag thu 6 tro di."""
        doan, da_co, bo = [], set(), []

        def them_tag(ten):
            if self._k(ten) in da_co or len(da_co) >= self.TOI_DA_HASHTAG:
                bo.append(ten)
                return
            da_co.add(self._k(ten))
            doan.append(["tag", ten])

        for i, p in enumerate(self.RE_HASHTAG.split(self.title or "")):
            if i % 2 == 0:
                if p:
                    doan.append(["chu", p])
            else:
                them_tag(p)
        tag_rieng = [str(t).strip().lstrip("#") for t in (self.tags or []) if str(t).strip().lstrip("#")]
        if tag_rieng:
            doan.append(["chu", "\n" if not da_co else " "])
            for t in tag_rieng:
                them_tag(t)
        # sau 1 hashtag TikTok tu them dau cach -> bo dau cach dau doan chu ke tiep (tranh 2 dau cach)
        gon = []
        for d in doan:
            if d[0] == "chu" and gon and gon[-1][0] == "tag":
                d = ["chu", re.sub(r"^[ \t　 ]+", "", d[1])]
            if d[0] == "chu" and not d[1]:
                continue
            gon.append(d)
        if bo:
            tiktok_logger.warning("  [-] bo hashtag (trung hoac qua 5 tag TikTok cho phep): " + " ".join("#" + t for t in bo))
        return gon, bo

    async def _chu_editor(self, editor):
        try:
            return (await editor.inner_text(timeout=3000)).rstrip("\n")
        except Exception:
            return ""

    async def go_hashtag(self, page, editor, ten):
        """Dan '#ten', cho bang goi y cua TikTok, chon dung muc '#ten' -> hashtag that (chu dam, bam duoc).
        Khong go tung chu: TikTok hay nuot 1 chu khi bang goi y bat len (vd '#經濟懶人包' -> '#經懶人包')."""
        muc = "#" + ten
        hop = page.locator("div[class*='mention-list-popover']")
        for lan in range(3):
            await page.keyboard.insert_text(muc)
            await asyncio.sleep(0.5)
            t = await self._chu_editor(editor)
            if self._k(t).endswith(self._k(muc)):
                break
            cum = t.split()[-1] if t and not t[-1].isspace() else ""
            tiktok_logger.warning(f"  [-] {muc}: o caption thanh '{cum}' -> xoa, dan lai")
            for _ in range(len(cum)):
                await page.keyboard.press("Backspace")
            await asyncio.sleep(0.5)
        else:
            await page.keyboard.type(" ")
            return "sai_chu"
        try:
            await hop.first.wait_for(state="visible", timeout=4000)
        except Exception:
            await page.keyboard.type(" ")       # danh thuc bang goi y: go dau cach roi xoa
            await page.keyboard.press("Backspace")
            try:
                await hop.first.wait_for(state="visible", timeout=4000)
            except Exception:
                tiktok_logger.warning(f"  [-] {muc}: TikTok khong hien goi y -> de chu thuong")
                await page.keyboard.type(" ")
                return "khong_goi_y"
        dong, vt = [], None
        for lan in range(4):  # danh sach goi y co luc tai cham (lan dau con ket qua cu) -> doc lai toi da 4 lan
            await asyncio.sleep(1.5)
            try:
                chu = await hop.first.inner_text(timeout=3000)
            except Exception:
                chu = ""
            dong = [d.strip() for d in chu.splitlines() if d.strip().startswith("#")]
            vt = next((i for i, d in enumerate(dong) if self._k(d.split()[0]) == self._k("#" + ten)), None)
            if vt is not None:
                break
        if dong and vt is None:
            tiktok_logger.warning(f"  [-] #{ten}: goi y khong co dung tag ({' | '.join(dong[:5])}) -> de chu thuong")
            await page.keyboard.type(" ")
            return "khong_khop"
        if not dong and not await hop.first.is_visible():
            await page.keyboard.type(" ")  # bang goi y da tat -> Enter se thanh xuong dong, khong bam
            return "khong_goi_y"
        for _ in range(vt or 0):
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.2)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)
        try:
            t = (await editor.inner_text(timeout=3000)).rstrip("\n")
        except Exception:
            t = ""
        if t and not t[-1].isspace():
            await page.keyboard.type(" ")
        return "ok" if dong else "ok_enter"

    async def add_title_tags(self, page):

        editor_locator = self.locator_base.locator('div.public-DraftEditor-content')
        # Tai khoan moi: TikTok bat hop thoai ngay sau khi chon video (vd moi bat 'tu dong kiem tra noi dung') che o caption
        for lan in range(6):
            await asyncio.sleep(1)
            if await self.dong_hop_thoai_dau(page, manh=lan >= 3):
                await asyncio.sleep(1)
            try:
                await editor_locator.click(timeout=6000)
                break
            except Exception:
                if lan == 5:
                    raise RuntimeError("HOP_THOAI_CHE: hop thoai cua TikTok che o caption, may khong dong duoc")

        await page.keyboard.press("End")
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Delete")
        await page.keyboard.press("End")
        await page.wait_for_timeout(1000)

        doan, bo = self.tach_caption()
        kq = []
        for loai, x in doan:
            if loai == "chu":
                await page.keyboard.insert_text(x)
                await page.wait_for_timeout(300)
            else:
                r = await self.go_hashtag(page, editor_locator, x)
                kq.append(f"#{x}:{r}")
        try:
            so_that = await editor_locator.locator("span.mention").count()
        except Exception:
            so_that = -1
        tiktok_logger.info(f"  [-] hashtag ({so_that} tag that): " + (", ".join(kq) or "khong co"))
        self.thu["so_hashtag_that"] = so_that
        self.thu["hashtag"] = kq
        self.thu["hashtag_bo"] = bo
        try:
            self.thu["caption_html"] = (await editor_locator.inner_html(timeout=3000))[:4000]
        except Exception:
            pass

    async def upload_thumbnails(self, page):
        await self.locator_base.locator(".cover-container").click()
        await self.locator_base.locator(".cover-edit-container >> text=Upload cover").click()
        async with page.expect_file_chooser() as fc_info:
            await self.locator_base.locator(".upload-image-upload-area").click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.thumbnail_path)
        await self.locator_base.locator('div.cover-edit-panel:not(.hide-panel)').get_by_role(
            "button", name="Confirm").click()
        await page.wait_for_timeout(3000)  # wait 3s, fix it later

    async def change_language(self, page):
        # set the language to english
        await page.goto("https://www.tiktok.com")
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_selector('[data-e2e="nav-more-menu"]')
        # 已经设置为英文, 省略这个步骤
        if await page.locator('[data-e2e="nav-more-menu"]').text_content() == "More":
            return

        await page.locator('[data-e2e="nav-more-menu"]').click()
        await page.locator('[data-e2e="language-select"]').click()
        await page.locator('#creator-tools-selection-menu-header >> text=English (US)').click()

    # Luat chu kenh 16/11/2026: KHONG gan nhan AI, KHONG them vi tri, KHONG chon do tuoi.
    TU_KHOA_NHAN = re.compile(r"(?-i:\bAI\b)|AI-generated|AIGC|AI\s?生成|人工智慧|\blabel|標籤|标签|nhãn|synthetic|disclos"
                              r"|\blocation\b|vị trí|位置|地點|\baudience\b|age restriction|18\+", re.I)
    NUT_TU_CHOI_NHAN = ["Cancel", "Not now", "No", "No thanks", "Skip", "Don't add", "Don't label", "Later", "Close",
                        "取消", "略過", "稍後再說", "Hủy", "Bỏ qua", "Để sau"]

    async def tu_choi_hop_thoai_nhan(self, page, hop, chu) -> bool:
        """Hop thoai noi ve nhan AI / vi tri / do tuoi -> CHI bam nut tu choi (khong co thi Esc), khong bao gio bam dong y.
        Tra ve True neu da xu ly hop thoai nay."""
        if not self.TU_KHOA_NHAN.search(chu or ""):
            return False
        tiktok_logger.warning("  [-] hop thoai ve nhan AI/vi tri/do tuoi -> chi tu choi: " + (chu or "")[:200].replace("\n", " | "))
        for t in self.NUT_TU_CHOI_NHAN:
            b = hop.locator("button").filter(has_text=re.compile(r"^\s*" + re.escape(t) + r"\s*$", re.I))
            if await b.count():
                await b.first.click(force=True)
                tiktok_logger.info(f"  [-] da bam '{t}' (tu choi nhan)")
                await asyncio.sleep(1)
                return True
        await page.keyboard.press("Escape")
        tiktok_logger.info("  [-] da bam Esc (tu choi nhan)")
        await asyncio.sleep(1)
        return True

    async def dong_hop_thoai_dau(self, page, manh=False):
        """Hop thoai TikTok hien NGAY SAU khi chon video (truoc khi dien caption): tu choi / de sau / dong lai,
        KHONG bat cai dat nao cua tai khoan. manh=True (da thu vai lan khong duoc): dung them cach cua dong_hop_thoai.
        Tra ve True neu vua xu ly 1 hop thoai."""
        TU_CHOI = ["Cancel", "Not now", "Later", "Maybe later", "Skip", "No thanks", "Close", "Got it", "OK",
                   "取消", "稍後再說", "略過", "知道了", "Hủy", "Để sau", "Bỏ qua", "Đã hiểu"]
        for base in (self.locator_base, page):
            try:
                hop = base.locator('.TUXModal, [role="dialog"]').filter(has=base.locator("button")).last
                if not await hop.count() or not await hop.is_visible():
                    continue
                chu = (await hop.inner_text())[:300].replace("\n", " | ")
                nut = []
                for b in await hop.locator("button").all():
                    try:
                        nut.append((await b.inner_text()).strip()[:30])
                    except Exception:
                        pass
                tiktok_logger.info(f"  [-] hop thoai truoc khi dang: {chu} || nut: {nut}")
                if await self.tu_choi_hop_thoai_nhan(page, hop, chu):
                    return True
                for t in TU_CHOI:
                    btn = hop.locator("button").filter(has_text=re.compile(r"^\s*" + re.escape(t) + r"\s*$", re.I))
                    if await btn.count():
                        await btn.first.click(force=True)
                        tiktok_logger.info(f"  [-] da bam '{t}' (khong doi cai dat tai khoan)")
                        return True
                dong = hop.locator('[aria-label*="lose" i], [data-e2e*="close" i]')
                if await dong.count():
                    await dong.first.click(force=True)
                    tiktok_logger.info("  [-] da bam nut dong (X)")
                    return True
                for b in await hop.locator("button").all():      # nut chi co bieu tuong (khong chu) = nut X
                    try:
                        if not (await b.inner_text()).strip():
                            await b.click(force=True)
                            tiktok_logger.info("  [-] da bam nut khong chu (X)")
                            return True
                    except Exception:
                        pass
                await page.keyboard.press("Escape")
                if manh:
                    await asyncio.sleep(1)
                    await self.dong_hop_thoai(page)
                return True
            except Exception:
                continue
        return False

    async def dong_hop_thoai(self, page):
        """TikTok hay bat hop thoai (TUXModal) che nut Post: bam nut xac nhan an toan, khong thi bam Esc."""
        CHON = ["Post now", "Post anyway", "Continue", "Got it", "OK", "Confirm", "Done",
                "立即發佈", "發佈", "繼續", "知道了", "確定", "Đăng ngay", "Tiếp tục", "Đã hiểu"]
        for base in (self.locator_base, page):
            try:
                hop = base.locator('.TUXModal, [role="dialog"]').filter(has=base.locator("button")).last
                if not await hop.count() or not await hop.is_visible():
                    continue
                try:
                    chu = await hop.inner_text()
                except Exception:
                    chu = ""
                tiktok_logger.info("  [-] hop thoai: " + chu[:200].replace("\n", " | "))
                if await self.tu_choi_hop_thoai_nhan(page, hop, chu):
                    return True
                if "copyright check" in chu.lower():
                    now_t = asyncio.get_event_loop().time()
                    self._bq = getattr(self, "_bq", None) or now_t
                    if now_t - self._bq < 180:  # cho TikTok kiem ban quyen xong (toi da 3 phut)
                        for t in ("Cancel", "Wait", "Hủy", "取消"):
                            b = hop.locator("button").filter(has_text=re.compile(r"^\s*" + t + r"\s*$", re.I))
                            if await b.count():
                                await b.first.click(force=True); break
                        else:
                            await page.keyboard.press("Escape")
                        tiktok_logger.info("  [-] cho kiem tra ban quyen xong...")
                        await asyncio.sleep(15)
                        return True
                for t in CHON:
                    btn = hop.locator("button").filter(has_text=re.compile(r"^\s*" + re.escape(t) + r"\s*$", re.I))
                    if await btn.count():
                        await btn.first.click(force=True)
                        tiktok_logger.info(f"  [-] da bam '{t}' trong hop thoai")
                        await asyncio.sleep(1)
                        return True
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
                return True
            except Exception:
                continue
        return False

    async def nut_post(self):
        """Nut Post: uu tien nut TikTok danh dau san (data-e2e); khong co thi lay nut dau tien nhu cu,
        nhung KHONG bam neu chu tren nut la Discard / Save draft / Cancel (TikTok doi thu tu nut)."""
        nut = self.locator_base.locator('button[data-e2e="post_video_button"]')
        if not await nut.count():
            nut = self.locator_base.locator('div.button-group button')
            if not await nut.count():
                return None
        nut = nut.nth(0)
        try:
            chu = (await nut.inner_text(timeout=3000)).strip()
        except Exception:
            chu = ""
        if re.search(r"discard|draft|cancel", chu, re.I):
            raise RuntimeError(f"NUT_POST_LA: nut dau tien khong phai Post ma la '{chu[:30]}'")
        return nut

    async def click_publish(self, page):
        han = asyncio.get_event_loop().time() + 360  # toi da 6 phut (gom 3 phut cho kiem ban quyen)
        while True:
            try:
                await self.dong_hop_thoai(page)
                publish_button = await self.nut_post()
                if publish_button is not None:
                    if self.khi_bam_post:
                        try:
                            self.khi_bam_post()      # ghi dau TRUOC khi bam: tu day tro di coi nhu "co the da dang"
                        except Exception:
                            pass
                        self.khi_bam_post = None
                    await publish_button.click(timeout=5000)
                await asyncio.sleep(1)
                await self.dong_hop_thoai(page)  # hop thoai hien SAU khi bam Post (vd "Post now?")
                await page.wait_for_url("https://www.tiktok.com/tiktokstudio/content", timeout=5000)
                tiktok_logger.success("  [-] video published success")
                break
            except Exception as e:
                if asyncio.get_event_loop().time() > han:
                    raise RuntimeError("Khong bam duoc nut Post sau 6 phut (hop thoai TikTok che nut?): " + str(e).strip().splitlines()[0][:120] if str(e).strip() else "Khong bam duoc nut Post sau 6 phut") from e
                tiktok_logger.info(f"  [-] video publishing ({type(e).__name__})")
                await asyncio.sleep(1)

    # ------------------------------------------------------------ kiem tra that
    async def _nghe_ds_bai(self, r):
        """Nghe API danh sach bai cua TikTok Studio (trang Posts tu goi) de biet bai nao da len that."""
        if "creator/manage/item_list" not in r.url:
            return
        try:
            j = await r.json()
            if not isinstance(j, dict) or j.get("status_code") not in (0, None):
                return                      # TikTok bao loi -> khong tinh la da doc duoc danh sach
            gio = (j.get("extra") or {}).get("now")
            if gio:
                self._lech = float(gio) / 1000 - time.time()
            for it in (j.get("item_list") or []):
                if it.get("item_id"):
                    self._items[str(it["item_id"])] = it
            self._so_lan_ds += 1
        except Exception:
            pass

    async def kiem_tai_khoan(self, page):
        """Hoi TikTok: file dang nhap nay dang o tai khoan nao. Sai tai khoan / het han -> bao loi, khong dang."""
        js = """async()=>{try{const r=await fetch('https://www.tiktok.com/passport/web/account/info/?aid=1459',{credentials:'include'});return await r.text()}catch(e){return ''}}"""
        user = None
        for _ in range(3):
            try:
                d = (json.loads(await page.evaluate(js) or "{}").get("data") or {})
                user = d.get("username")
                if user:
                    break
            except Exception:
                pass
            await asyncio.sleep(2)
        self.account_username = user
        tiktok_logger.info(f"tai_khoan: {user}")
        want = (self.expected_username or "").lstrip("@").lower()
        if not user:
            raise RuntimeError("HET_HAN_DANG_NHAP: TikTok khong cho biet tai khoan (dang nhap het han?)")
        if want and user.lower() != want:
            raise RuntimeError(f"SAI_TAI_KHOAN: file dang nhap dang o @{user}, can @{want}")

    async def tai_ds_bai(self, page, cho=25):
        """Mo (lai) trang Posts de TikTok tra danh sach bai moi nhat. True = da nhan duoc danh sach.
        TikTok tra danh sach thanh 3-5 phan hoi -> cho toi khi im 3 giay (toi da 15 giay) moi coi la du."""
        truoc = self._so_lan_ds
        try:
            await page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            tiktok_logger.info(f"  [-] mo trang Posts loi ({type(e).__name__})")
        loop = asyncio.get_event_loop()
        han = loop.time() + cho
        while self._so_lan_ds == truoc and loop.time() < han:
            await asyncio.sleep(0.5)
        if self._so_lan_ds == truoc:
            return False
        han = loop.time() + 15
        while loop.time() < han:
            n = self._so_lan_ds
            await asyncio.sleep(3)
            if self._so_lan_ds == n:
                break
        return True

    SAI_GIO = 300   # giay tru hao: dong ho lech / TikTok ghi gio tao som hon luc bam

    def tim_bai(self, chi_bai_moi=False):
        """Tim bai cua CHINH video nay trong danh sach Posts. Tra ve id bai hoac None.
        - Truoc khi dang (chi_bai_moi=False): bai tao tu luc bat dau thu dang video nay (self.tu_luc) va caption trung
          40 ky tu dau. Bai cu hon (ke ca cung caption, ke ca bai da an 'Only me' tu truoc) KHONG tinh.
        - Sau khi bam Post (chi_bai_moi=True): chi xet bai CHUA co trong danh sach chup truoc khi tai video len va tao
          sau luc chup. Uu tien bai trung caption; khong co ma chi co DUNG 1 bai moi thi nhan bai do
          (TikTok co the tu sua caption) - de khong dang lai lan 2."""
        if chi_bai_moi:
            tu = (self._luc_chup or time.time()) - self.SAI_GIO
        else:
            tu = (self.tu_luc or time.time()) - self.SAI_GIO
        ung = []
        for it in self._items.values():
            try:
                ct = int(it.get("create_time") or 0) - self._lech      # doi sang gio may
            except Exception:
                continue
            iid = str(it["item_id"])
            if ct < tu or (chi_bai_moi and iid in (self._ids_truoc or ())):
                continue
            ung.append((ct, iid, khop_caption(self.title, it.get("desc"))))
        khop = [u for u in ung if u[2]]
        if khop:
            if chi_bai_moi and len(khop) > 1:
                self.bai_trung = sorted(u[1] for u in khop)     # 2 bai moi cung caption -> co the da dang trung
            return max(khop)[1]
        if chi_bai_moi and len(ung) == 1:
            tiktok_logger.info("  [-] caption TikTok tra ve khac caption goc, nhung day la bai moi duy nhat -> nhan")
            return ung[0][1]
        return None

    async def xac_nhan_bai(self, page, toi_da=180):
        """Sau khi bam Post: cho toi khi bai MOI xuat hien that trong danh sach Posts. Khong thay -> None."""
        han = asyncio.get_event_loop().time() + toi_da
        await asyncio.sleep(3)
        while True:
            vid = self.tim_bai(chi_bai_moi=True)
            if vid:
                return vid
            if asyncio.get_event_loop().time() > han:
                return None
            await asyncio.sleep(8)
            await self.tai_ds_bai(page)

    async def detect_upload_status(self, page):
        han = asyncio.get_event_loop().time() + 12 * 60   # qua 12 phut chua tai xong -> bao loi ro rang (chua bam Post)
        while True:
            if asyncio.get_event_loop().time() > han:
                raise RuntimeError("TAI_LEN_QUA_LAU: video tai len TikTok qua 12 phut chua xong (mang cham?) - chua bam Post")
            try:
                # if await self.locator_base.locator('div.btn-post > button').get_attribute("disabled") is None:
                if await self.locator_base.locator(
                        'div.button-group > button >> text=Post').get_attribute("disabled") is None:
                    tiktok_logger.info("  [-]video uploaded.")
                    break
                else:
                    tiktok_logger.info("  [-] video uploading...")
                    await asyncio.sleep(2)
                    if await self.locator_base.locator(
                            'button[aria-label="Select file"]').count():
                        tiktok_logger.info("  [-] found some error while uploading now retry...")
                        await self.handle_upload_error(page)
            except:
                tiktok_logger.info("  [-] video uploading...")
                await asyncio.sleep(2)

    async def choose_base_locator(self, page):
        # await page.wait_for_selector('div.upload-container')
        if await page.locator('iframe[data-tt="Upload_index_iframe"]').count():
            self.locator_base = page.frame_locator(Tk_Locator.tk_iframe)
        else:
            self.locator_base = page.locator(Tk_Locator.default) 

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
