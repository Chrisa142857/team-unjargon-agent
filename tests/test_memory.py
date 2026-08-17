import unittest

from app.memory import InMemoryTeamMemory


class TeamMemoryTests(unittest.TestCase):
    def setUp(self):
        self.memory = InMemoryTeamMemory()

    def test_correction_changes_next_retrieval_without_context(self):
        record = self.memory.save_correction("team", "ADR", "A recorded architecture choice.", "Member A")
        self.assertEqual(record.definition, "A recorded architecture choice.")
        later = self.memory.get_term("team", "adr")
        self.assertEqual(later.definition, "A recorded architecture choice.")
        self.assertFalse(hasattr(later, "context"))

    def test_useful_increment_is_term_level_only(self):
        self.memory.save_correction("team", "ADR", "A recorded architecture choice.", "Member A")
        updated = self.memory.mark_useful("team", "ADR", "Member B")
        self.assertEqual(updated.helpful_count, 1)
        self.assertNotIn("transcript", vars(updated))


if __name__ == "__main__":
    unittest.main()
