import json
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.content import LearningItem, LearningSection, SectionItem
from app.models.enums import LearningItemKind, ContentSource, Difficulty

# --- Content Data ---
FUNDAMENTALS = [
    {"title": "What is a variable?", "content": "A variable is a container for storing data values."},
    {"title": "Data types in programming", "content": "Common types include integers, floats, strings, and booleans."},
    {"title": "Operators and expressions", "content": "Use +, -, *, / to perform math. Use == to compare."},
    {"title": "Conditional statements", "content": "If/else statements execute code based on a condition."},
    {"title": "For and while loops", "content": "Loops repeat a block of code multiple times."},
    {"title": "Nested loops", "content": "A loop inside another loop. Useful for 2D arrays."},
    {"title": "Functions and methods", "content": "Reusable blocks of code that perform a specific task."},
    {"title": "Parameters and arguments", "content": "Parameters are the variables in the function definition."},
    {"title": "Introduction to arrays", "content": "An array is a collection of elements identified by index."},
    {"title": "Basics of time and space complexity", "content": "Big O notation describes the performance of an algorithm."},
]

ARRAYS = [
    ("Two Sum", "https://leetcode.com/problems/two-sum/", Difficulty.EASY),
    ("Running Sum of 1D Array", "https://leetcode.com/problems/running-sum-of-1d-array/", Difficulty.EASY),
    ("Richest Customer Wealth", "https://leetcode.com/problems/richest-customer-wealth/", Difficulty.EASY),
    ("Concatenation of Array", "https://leetcode.com/problems/concatenation-of-array/", Difficulty.EASY),
    ("Build Array from Permutation", "https://leetcode.com/problems/build-array-from-permutation/", Difficulty.EASY),
    ("Find Numbers with Even Number of Digits", "https://leetcode.com/problems/find-numbers-with-even-number-of-digits/", Difficulty.EASY),
    ("Number of Good Pairs", "https://leetcode.com/problems/number-of-good-pairs/", Difficulty.EASY),
    ("Move Zeroes", "https://leetcode.com/problems/move-zeroes/", Difficulty.EASY),
    ("Remove Duplicates from Sorted Array", "https://leetcode.com/problems/remove-duplicates-from-sorted-array/", Difficulty.EASY),
    ("Best Time to Buy and Sell Stock", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/", Difficulty.EASY),
    ("Contains Duplicate", "https://leetcode.com/problems/contains-duplicate/", Difficulty.EASY),
    ("Maximum Subarray", "https://leetcode.com/problems/maximum-subarray/", Difficulty.MEDIUM),
]

STRINGS = [
    ("Reverse String", "https://leetcode.com/problems/reverse-string/", Difficulty.EASY),
    ("Valid Palindrome", "https://leetcode.com/problems/valid-palindrome/", Difficulty.EASY),
    ("Valid Anagram", "https://leetcode.com/problems/valid-anagram/", Difficulty.EASY),
    ("Jewels and Stones", "https://leetcode.com/problems/jewels-and-stones/", Difficulty.EASY),
    ("Defanging an IP Address", "https://leetcode.com/problems/defanging-an-ip-address/", Difficulty.EASY),
    ("Ransom Note", "https://leetcode.com/problems/ransom-note/", Difficulty.EASY),
    ("Find the Index of the First Occurrence in a String", "https://leetcode.com/problems/find-the-index-of-the-first-occurrence-in-a-string/", Difficulty.MEDIUM),
    ("Longest Common Prefix", "https://leetcode.com/problems/longest-common-prefix/", Difficulty.EASY),
    ("Is Subsequence", "https://leetcode.com/problems/is-subsequence/", Difficulty.EASY),
    ("First Unique Character in a String", "https://leetcode.com/problems/first-unique-character-in-a-string/", Difficulty.EASY),
]

def load_content():
    db: Session = SessionLocal()
    try:
        # Get section IDs
        fund_sec = db.query(LearningSection).filter_by(slug="fundamentals").first()
        arr_sec = db.query(LearningSection).filter_by(slug="arrays").first()
        str_sec = db.query(LearningSection).filter_by(slug="strings").first()

        if not fund_sec or not arr_sec or not str_sec:
            print("Error: Sections not found. Run migrations first.")
            return

        # Clear existing items to avoid duplicates if run multiple times
        db.query(SectionItem).filter(SectionItem.section_id.in_([fund_sec.id, arr_sec.id, str_sec.id])).delete()
        db.query(LearningItem).filter(LearningItem.topic_id.in_([fund_sec.topic_id, arr_sec.topic_id, str_sec.topic_id])).delete()
        db.commit()

        # 1. Load Fundamentals
        for i, item in enumerate(FUNDAMENTALS):
            li = LearningItem(
                topic_id=fund_sec.topic_id, kind=LearningItemKind.LESSON, source=ContentSource.INTERNAL,
                title=item["title"], content_md=item["content"], is_active=True
            )
            db.add(li)
            db.flush()
            db.add(SectionItem(section_id=fund_sec.id, item_id=li.id, order_index=i+1, is_required=True))

        # 2. Load Arrays
        for i, (title, url, diff) in enumerate(ARRAYS):
            li = LearningItem(
                topic_id=arr_sec.topic_id, kind=LearningItemKind.EXTERNAL_PROBLEM, source=ContentSource.LEETCODE,
                title=title, external_url=url, difficulty=diff, is_active=True
            )
            db.add(li)
            db.flush()
            db.add(SectionItem(section_id=arr_sec.id, item_id=li.id, order_index=i+1, is_required=True))

        # 3. Load Strings
        for i, (title, url, diff) in enumerate(STRINGS):
            li = LearningItem(
                topic_id=str_sec.topic_id, kind=LearningItemKind.EXTERNAL_PROBLEM, source=ContentSource.LEETCODE,
                title=title, external_url=url, difficulty=diff, is_active=True
            )
            db.add(li)
            db.flush()
            db.add(SectionItem(section_id=str_sec.id, item_id=li.id, order_index=i+1, is_required=True))

        db.commit()
        print("Successfully loaded all learning content into the database!")
    
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_content()