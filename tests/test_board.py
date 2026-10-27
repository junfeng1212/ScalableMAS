import asyncio

from teamboard.board import MessageBoard


def test_unread_skips_own_posts_and_follows_the_cursor(tmp_path):
    board = MessageBoard(tmp_path / "board.jsonl")
    board.post("Bob", "I take the 1990s documents")
    board.post("Eric", "doc 12 mentions the award")

    assert [m.content for m in board.unread("Bob", after_id=0)] == ["doc 12 mentions the award"]
    assert board.unread("Bob", after_id=2) == []
    assert len((tmp_path / "board.jsonl").read_text().splitlines()) == 2
    assert (tmp_path / "board.txt").read_text().startswith("#1 [00:00] Bob: I take the 1990s documents\n\n#2 [00:00] Eric:")


def test_wait_wakes_on_a_teammate_post_and_times_out(tmp_path):
    async def scenario():
        board = MessageBoard(tmp_path / "board.jsonl")
        loop = asyncio.get_running_loop()
        loop.call_later(0.05, board.post, "Bob", "my own post does not wake me")
        loop.call_later(0.10, board.post, "Eric", "hello Bob")
        woken = await board.wait_for_unread("Bob", after_id=0, timeout=5)
        timed_out = await board.wait_for_unread("Bob", after_id=2, timeout=0.05)
        return woken, timed_out

    woken, timed_out = asyncio.run(scenario())
    assert [m.content for m in woken] == ["hello Bob"]
    assert timed_out == []
