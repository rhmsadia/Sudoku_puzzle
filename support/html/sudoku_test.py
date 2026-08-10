import unittest

from sudoku_ai import (
    compare_solve_modes,
    format_solution,
    generate_puzzle,
    get_hint,
    parse_grid,
    solve_sudoku,
    solve_sudoku_with_stats,
    validate_grid,
)


class TestSudokuSolver(unittest.TestCase):
    def test_solve_example(self):
        puzzle = (
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079"
        )
        solution = solve_sudoku(puzzle)
        self.assertTrue(all(len(solution[s]) == 1 for s in solution))
        self.assertEqual(solution["A1"], "5")
        self.assertEqual(solution["I9"], "9")

    def test_invalid_puzzle(self):
        invalid = "1" * 81
        with self.assertRaises(ValueError):
            solve_sudoku(invalid)

    def test_format_solution(self):
        values = parse_grid(
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079"
        )
        self.assertIn("5", format_solution(values))

    def test_validate_grid(self):
        self.assertTrue(validate_grid("530070000600195000098000060800060003400803001700020006060000280000419005000080079"))

    def test_solve_with_stats(self):
        result = solve_sudoku_with_stats(
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079",
            mode="heuristics",
        )
        self.assertTrue(result["stats"]["solved"])
        self.assertGreater(result["stats"]["backtracks"], -1)
        self.assertEqual(result["solution"]["A1"], "5")

    def test_compare_modes(self):
        results = compare_solve_modes(
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079"
        )
        self.assertEqual(len(results), 3)
        self.assertTrue(all(item["stats"]["solved"] for item in results))

    def test_hint_and_generation(self):
        puzzle = (
            "530070000"
            "600195000"
            "098000060"
            "800060003"
            "400803001"
            "700020006"
            "060000280"
            "000419005"
            "000080079"
        )
        hint = get_hint(puzzle)
        self.assertIsNotNone(hint)
        self.assertIn("square", hint)
        self.assertIn("digit", hint)
        generated = generate_puzzle("easy")
        self.assertEqual(len(generated), 81)
        self.assertTrue(validate_grid(generated))


if __name__ == "__main__":
    unittest.main()
