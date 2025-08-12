import azure.functions as func
import logging
import os
from datetime import datetime, timezone, timedelta
from shared.config import Config
from shared.firestore_client import get_firestore_client
from shared.x_api_client import (
    XAPIClient,
    XAPIError,
    RateLimitError,
    AuthenticationError,
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp()


def process_scheduled_posts(target_slot: int = None, target_date: str = None) -> dict:
    """
    予約投稿の処理を実行する共通ロジック

    Args:
        target_slot: 対象の時間スロット（None の場合は現在時刻で判定）
        target_date: 対象日付（None の場合は今日）

    Returns:
        処理結果の辞書 (success_count, error_count, messages)
    """
    # JST (Asia/Tokyo) タイムゾーンで現在時刻を取得
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)

    # 対象の時間スロットを決定
    if target_slot is None:
        current_slot = Config.get_current_time_slot(now)
        if current_slot is None:
            return {
                "success_count": 0,
                "error_count": 0,
                "messages": [
                    f'Current time {now.strftime("%H:%M")} is not a posting slot'
                ],
            }
    else:
        current_slot = target_slot

    # 対象日付を決定
    if target_date is None:
        target_date = now.strftime("%Y/%m/%d")

    logger.info(f"Processing posts for slot {current_slot} on {target_date}")

    messages = []

    try:
        # Firestore接続
        fs_client = get_firestore_client()

        # 該当する投稿を取得
        posts = fs_client.get_scheduled_posts(
            date_str=target_date, time_slot=current_slot
        )

        if not posts:
            message = (
                f"No scheduled posts found for slot {current_slot} on {target_date}"
            )
            logger.info(message)
            messages.append(message)
            return {"success_count": 0, "error_count": 0, "messages": messages}

        logger.info(f"Found {len(posts)} scheduled posts to process")
        messages.append(f"Found {len(posts)} scheduled posts to process")

        success_count = 0
        error_count = 0

        for post in posts:
            try:
                # ユーザートークン取得
                token = (
                    fs_client.get_user_token()
                )  # デフォルトユーザー "main_user" を使用

                if not token:
                    error_msg = f"No access token found for post {post['id']}"
                    logger.error(error_msg)
                    messages.append(error_msg)
                    fs_client.update_post_status(
                        post_id=post["id"],
                        is_posted=False,
                        error_message="アクセストークンが見つかりません",
                    )
                    error_count += 1
                    continue

                # X API投稿
                with XAPIClient(token) as x_client:
                    result = x_client.post_tweet(post["content"])

                    # ステータス更新
                    fs_client.update_post_status(
                        post_id=post["id"],
                        is_posted=True,
                        x_post_id=result["data"]["id"],
                    )

                    success_count += 1
                    success_msg = f"Successfully posted: {post['id']} -> X Post ID: {result['data']['id']}"
                    logger.info(success_msg)
                    messages.append(success_msg)

            except AuthenticationError as e:
                error_msg = f"Authentication error for post {post['id']}: {str(e)}"
                logger.error(error_msg)
                messages.append(error_msg)
                fs_client.update_post_status(
                    post_id=post["id"],
                    is_posted=False,
                    error_message=f"認証エラー: {str(e)}",
                )
                error_count += 1

            except RateLimitError as e:
                error_msg = f"Rate limit exceeded for post {post['id']}: {str(e)}"
                logger.error(error_msg)
                messages.append(error_msg)
                fs_client.update_post_status(
                    post_id=post["id"],
                    is_posted=False,
                    error_message=f"レート制限エラー: {str(e)}",
                )
                error_count += 1

            except XAPIError as e:
                error_msg = f"X API error for post {post['id']}: {str(e)}"
                logger.error(error_msg)
                messages.append(error_msg)
                fs_client.update_post_status(
                    post_id=post["id"],
                    is_posted=False,
                    error_message=f"X APIエラー: {str(e)}",
                )
                error_count += 1

            except Exception as e:
                error_msg = f"Unexpected error for post {post['id']}: {str(e)}"
                logger.error(error_msg)
                messages.append(error_msg)
                fs_client.update_post_status(
                    post_id=post["id"],
                    is_posted=False,
                    error_message=f"予期しないエラー: {str(e)}",
                )
                error_count += 1

        summary_msg = (
            f"Auto posting completed. Success: {success_count}, Errors: {error_count}"
        )
        logger.info(summary_msg)
        messages.append(summary_msg)

        return {
            "success_count": success_count,
            "error_count": error_count,
            "messages": messages,
        }

    except Exception as e:
        error_msg = f"Fatal error in process_scheduled_posts: {str(e)}"
        logger.error(error_msg)
        messages.append(error_msg)
        return {"success_count": 0, "error_count": 1, "messages": messages}


@app.timer_trigger(
    schedule="0 0 0,3,6,12 * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def auto_poster(myTimer: func.TimerRequest) -> None:
    """自動投稿処理のメインエントリーポイント（Timer Trigger）ビルドされたか確認用"""

    logger.info("Auto poster timer function triggered")

    if myTimer.past_due:
        logger.warning("The timer is past due!")

    # JST (Asia/Tokyo) タイムゾーンで現在時刻を取得
    jst = timezone(timedelta(hours=9))

    # TimerRequestから実行時刻を取得（schedule_statusが利用可能な場合）
    # schedule_statusが利用できない場合は現在時刻を使用
    if hasattr(myTimer, "schedule_status") and myTimer.schedule_status:
        # Azure Functionsの仕様により、schedule_statusのtimestampはUTCで提供される
        execution_time = myTimer.schedule_status.last
        if execution_time:
            # UTCからJSTに変換
            execution_time_jst = execution_time.replace(tzinfo=timezone.utc).astimezone(
                jst
            )
        else:
            execution_time_jst = datetime.now(jst)
    else:
        execution_time_jst = datetime.now(jst)

    # UTC時間でのslot判定（CRON式に対応）
    utc_hour = (
        myTimer.schedule_status.last.hour
        if hasattr(myTimer, "schedule_status")
        and myTimer.schedule_status
        and myTimer.schedule_status.last
        else datetime.now(timezone.utc).hour
    )

    # UTC時間からJST時間スロットへのマッピング
    # UTC 00:00 = JST 09:00 -> slot 0
    # UTC 03:00 = JST 12:00 -> slot 1
    # UTC 06:00 = JST 15:00 -> slot 2
    # UTC 12:00 = JST 21:00 -> slot 3
    utc_to_slot_mapping = {
        0: 0,  # UTC 00:00 -> JST 09:00
        3: 1,  # UTC 03:00 -> JST 12:00
        6: 2,  # UTC 06:00 -> JST 15:00
        12: 3,  # UTC 12:00 -> JST 21:00
    }

    target_slot = utc_to_slot_mapping.get(utc_hour)

    if target_slot is None:
        logger.warning(
            f"Unexpected UTC hour {utc_hour} - Timer should only run at 0, 3, 6, or 12"
        )
        return

    target_date = execution_time_jst.strftime("%Y/%m/%d")

    # JST時間での実行時刻をログに記録
    jst_hour_mapping = {0: 9, 1: 12, 2: 15, 3: 21}
    jst_hour = jst_hour_mapping.get(target_slot, "Unknown")

    logger.info(
        f"Timer triggered at UTC {utc_hour}:00 (JST {jst_hour}:00, Slot: {target_slot}) - JST Date: {target_date}"
    )

    # 共通ロジックを実行（明示的にslotとdateを指定）
    result = process_scheduled_posts(target_slot=target_slot, target_date=target_date)

    if result["error_count"] > 0:
        logger.error(f"Timer execution completed with {result['error_count']} errors")
    else:
        logger.info("Timer execution completed successfully")


# テスト用HTTP Trigger（本番では無効化）
if os.getenv("ENABLE_TEST_FUNCTIONS", "false").lower() == "true":

    @app.route(route="test_auto_poster", methods=["GET", "POST"])
    def test_auto_poster(req: func.HttpRequest) -> func.HttpResponse:
        """テスト用HTTP Trigger（手動実行可能）"""

        logger.info("Test auto poster HTTP function triggered")

        try:
            # クエリパラメータから設定を取得
            target_slot = req.params.get("slot")
            target_date = req.params.get("date")

            # パラメータの変換
            if target_slot is not None:
                try:
                    target_slot = int(target_slot)
                    if target_slot not in [0, 1, 2, 3]:
                        return func.HttpResponse(
                            "Invalid slot parameter. Must be 0, 1, 2, or 3.",
                            status_code=400,
                        )
                except ValueError:
                    return func.HttpResponse(
                        "Invalid slot parameter. Must be an integer.", status_code=400
                    )

            # 共通ロジックを実行
            result = process_scheduled_posts(
                target_slot=target_slot, target_date=target_date
            )

            # レスポンスを作成
            response_data = {
                "status": "completed",
                "success_count": result["success_count"],
                "error_count": result["error_count"],
                "messages": result["messages"],
            }

            import json

            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False, indent=2),
                status_code=200,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        except Exception as e:
            logger.error(f"Error in test_auto_poster: {str(e)}")
            error_response = {"status": "error", "message": str(e)}
            import json

            return func.HttpResponse(
                json.dumps(error_response, ensure_ascii=False, indent=2),
                status_code=500,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
