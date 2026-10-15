import XCTest

final class DemoUITests: XCTestCase {
    override func setUpWithError() throws { continueAfterFailure = false }

    func testLaunchCalculationAndGameInteraction() {
        let app = XCUIApplication()
        app.launch()
        let calculation = app.staticTexts["calculation"]
        XCTAssertTrue(calculation.waitForExistence(timeout: 15))
        XCTAssertTrue(calculation.label.contains("42"))
        XCTAssertEqual(app.staticTexts["score"].label, "Energy: 0")
        app.buttons["collect"].tap()
        app.buttons["collect"].tap()
        app.buttons["collect"].tap()
        XCTAssertEqual(app.staticTexts["score"].label, "Energy: 3")
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Interactive game smoke"
        screenshot.lifetime = .keepAlways
        add(screenshot)
        app.buttons["reset"].tap()
        XCTAssertEqual(app.staticTexts["score"].label, "Energy: 0")
    }
}