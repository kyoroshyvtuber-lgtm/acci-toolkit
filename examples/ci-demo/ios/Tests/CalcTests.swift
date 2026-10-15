import XCTest
@testable import App

final class CalcTests: XCTestCase {
    func testMultiply() {
        XCTAssertEqual(Calc.mul(6, 7), 42)
        XCTAssertEqual(Calc.mul(-3, 7), -21)
        XCTAssertEqual(Calc.mul(0, 7), 0)
    }

    func testGameScoreAndReset() {
        var game = EnergyCounter()
        XCTAssertEqual(game.score, 0)
        game.collect()
        game.collect()
        XCTAssertEqual(game.score, 2)
        game.reset()
        XCTAssertEqual(game.score, 0)
    }

    func testScoreHasABound() {
        var game = EnergyCounter()
        for _ in 0..<10001 { game.collect() }
        XCTAssertEqual(game.score, 9999)
    }
}