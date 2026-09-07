import XCTest

final class RegressionUITests: XCTestCase {

    @MainActor
    private func openMoreTabItem(_ app: XCUIApplication, name: String) {
        let moreButton = app.tabBars.buttons["More"]
        XCTAssertTrue(moreButton.waitForExistence(timeout: 10), "More tab missing")
        moreButton.tap()
        let item = app.staticTexts[name]
        XCTAssertTrue(item.waitForExistence(timeout: 10), "\(name) missing from More list")
        item.tap()
    }

    @MainActor
    func testWorkingTabsStillRender() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)

        app.tabBars.buttons["Services"].tap()
        XCTAssertTrue(app.staticTexts["Services"].waitForExistence(timeout: 15), "Services tab failed to render")

        app.tabBars.buttons["Files"].tap()
        XCTAssertTrue(app.switches["Show hidden"].waitForExistence(timeout: 15), "Files tab failed to render")

        openMoreTabItem(app, name: "Logs")
        XCTAssertTrue(app.textFields["Service"].waitForExistence(timeout: 15), "Logs tab failed to render")

        openMoreTabItem(app, name: "Settings")
        let signOut = app.buttons["Sign Out"]
        var attempts = 0
        while !signOut.exists && attempts < 8 {
            app.swipeUp()
            attempts += 1
        }
        XCTAssertTrue(signOut.waitForExistence(timeout: 5), "Settings tab failed to render")
    }
}
