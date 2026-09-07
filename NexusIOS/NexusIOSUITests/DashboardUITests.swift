import XCTest

final class DashboardUITests: XCTestCase {

    @MainActor
    func testDashboardLoadsLiveMetrics() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)

        let overall = app.staticTexts["Overall Status"]
        XCTAssertTrue(overall.waitForExistence(timeout: 20), "Dashboard did not load after sign-in")

        XCTAssertTrue(app.staticTexts["CPU"].exists, "CPU metric missing")
        XCTAssertTrue(app.staticTexts["Memory"].exists, "CPU metric missing")
        XCTAssertTrue(app.staticTexts["Storage"].exists, "Storage section missing")
        XCTAssertTrue(app.staticTexts["System"].exists, "System section missing")
    }
}
