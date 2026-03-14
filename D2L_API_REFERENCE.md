# D2L Brightspace API — Student CLI Endpoint Reference

> **Host:** `https://kennesaw.view.usg.edu`
> **Tenant:** `857f39d7-a377-40a5-9272-5bb63ea6aafe`
> **Base:** `https://kennesaw.view.usg.edu/d2l/api/{product}/{version}/...`
> **Auth:** `Authorization: Bearer {jwt}` (~1hr expiry)
> **Scope:** Read-only GET endpoints accessible to students

---

## API Products & Versions

| Product | Code | Version | Scope |
|---------|------|---------|-------|
| Learning Platform | `lp` | `1.47` | Users, enrollments, org structure, groups |
| Learning Environment | `le` | `1.80` | Content, grades, dropbox, quizzes, discussions, calendar |
| Awards | `bas` | `2.2` | Badges, certificates |
| ePortfolio | `eP` | `2.3` | Artifacts, collections, reflections |
| Learning Repository | `lr` | `1.0` | SCORM/LOR objects |

> Call `GET /d2l/api/versions/` on your instance to confirm supported versions.

## Pagination

**Bookmark-based** (most endpoints):
```json
{
  "PagingInfo": { "Bookmark": "eyJ...", "HasMoreItems": true },
  "Items": [ ... ]
}
```
Pass `?bookmark={value}` on next call. Walk sequentially — no random page access.

**Page-number** (discussion posts only): `?pageSize=20&pageNumber=1`

---

## 1. Auth & Identity

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/users/whoami` | Current user (UserId, FirstName, LastName, UniqueName, ProfileIdentifier) |
| `GET /d2l/api/lp/{v}/profile/myProfile` | Full profile (nickname, bio, homepage, social links) |
| `GET /d2l/api/lp/{v}/profile/myProfile/image` | Profile image (`?size={px}` optional) |
| `GET /d2l/api/lp/{v}/users/mypronouns` | Pronoun selections |
| `GET /d2l/api/lp/{v}/users/mypronouns/visibility` | Pronoun display preference |

**whoami response:**
```json
{
  "Identifier": "123456",
  "FirstName": "Jane",
  "LastName": "Student",
  "UniqueName": "jstudent1",
  "ProfileIdentifier": "abc123"
}
```

---

## 2. Enrollments

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/lp/{v}/enrollments/myenrollments/` | `orgUnitTypeId`, `bookmark`, `sortBy`, `isActive`, `startDateTime`, `endDateTime`, `canAccess` | All enrolled org units |
| `GET /d2l/api/lp/{v}/enrollments/myenrollments/{orgUnitId}` | — | Single enrollment details |
| `GET /d2l/api/lp/{v}/enrollments/myenrollments/{orgUnitId}/access` | — | Abbreviated access info |
| `GET /d2l/api/lp/{v}/enrollments/myenrollments/{orgUnitId}/parentOrgUnits` | `bookmark` | Parent org units |

> **Tip:** `?canAccess=true&isActive=true` filters to currently accessible courses only.

**MyOrgUnitInfo response:**
```json
{
  "OrgUnit": {
    "Id": 3824526,
    "Type": { "Id": 3, "Code": "Course Offering", "Name": "Course Offering" },
    "Name": "Data Structures Section 04 Spring Semester 2026 CO",
    "Code": "CS2720_S26",
    "HomeUrl": "https://kennesaw.view.usg.edu/d2l/home/3824526"
  },
  "Access": {
    "IsActive": true,
    "StartDate": "2026-01-12T05:00:00.000Z",
    "EndDate": "2026-05-10T04:00:00.000Z",
    "CanAccess": true
  },
  "PinDate": null
}
```

---

## 3. Organization & Courses

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/organization/info` | Institution name, Id, timezone |
| `GET /d2l/api/lp/{v}/orgstructure/{orgUnitId}` | Org unit properties (name, code, type, path) |
| `GET /d2l/api/lp/{v}/orgstructure/{orgUnitId}/parents/` | Parent org units (`?ouTypeId=` filter) |
| `GET /d2l/api/lp/{v}/orgstructure/{orgUnitId}/ancestors/` | Ancestor chain |
| `GET /d2l/api/lp/{v}/orgstructure/{orgUnitId}/colours` | Color scheme for UI |
| `GET /d2l/api/lp/{v}/courses/{orgUnitId}` | Course offering details (name, code, dates, description) |
| `GET /d2l/api/lp/{v}/courses/{orgUnitId}/image` | Course banner image (`?width=`, `?height=`) |
| `GET /d2l/api/lp/{v}/roles/` | All user roles |
| `GET /d2l/api/lp/{v}/roles/{roleId}` | Specific role |
| `GET /d2l/api/lp/{v}/outypes/` | All org unit types |

---

## 4. Course Content

### Modules & Topics

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/content/root/` | Root-level modules |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/modules/{moduleId}` | Specific module |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/modules/{moduleId}/structure/` | Children (sub-modules + topics) |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/topics/{topicId}` | Specific topic metadata |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/topics/{topicId}/file` | **Download topic file** (`?stream=true`) |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/toc` | Full table of contents |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/bookmarks` | Bookmarked topics |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/recent` | Recently visited topics |
| `GET /d2l/api/le/{v}/{orgUnitId}/overview` | Course overview text |
| `GET /d2l/api/le/{v}/{orgUnitId}/overview/attachment` | Overview file attachment |

**Module structure response:**
```json
[
  { "Type": 0, "Id": 11111, "Title": "Week 1: Introduction", "IsHidden": false, "IsLocked": false },
  { "Type": 1, "Id": 22222, "Title": "Syllabus PDF", "TopicType": 1, "Url": "https://...", "DueDate": null }
]
```
`Type 0` = sub-module, `Type 1` = topic. `TopicType`: `1`=File, `2`=Link.

### Scheduled / Due Items

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/content/myItems/` | `completion`, `orgUnitIdsCSV`, `startDateTime`, `endDateTime` | Scheduled items across courses |
| `GET /d2l/api/le/{v}/content/myItems/due/` | same | Items with upcoming due dates |
| `GET /d2l/api/le/{v}/content/myItems/itemCounts/` | same | Item counts by org unit |
| `GET /d2l/api/le/{v}/content/myItems/due/itemCounts/` | same | Due item counts by org unit |
| `GET /d2l/api/le/{v}/content/myItems/completions/` | `orgUnitIdsCSV`, `completedFromDateTime`, `completedToDateTime` | Completed items |
| `GET /d2l/api/le/{v}/content/myItems/completions/due/` | same | Completed items that had due dates |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/myItems/` | `completion`, `startDateTime`, `endDateTime` | Scheduled items for one course |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/myItems/due/` | same | Due items for one course |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/myItems/itemCount` | same | Item count for one course |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/myItems/due/itemCount` | same | Due item count for one course |

### Overdue Items

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/overdueItems/myItems` | `orgUnitIdsCSV` | All my overdue items |

### Completions / Progress

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/content/completions/mycount/` | My completion count |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/userprogress/` | Progress across topics |
| `GET /d2l/api/le/{v}/{orgUnitId}/content/userprogress/{topicId}` | Progress on a specific topic |

---

## 5. Grades

### My Grades

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/values/myGradeValues/` | — | **All my grades in a course** |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/{gradeObjectId}/values/myGradeValue` | — | My grade for one item |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/final/values/myGradeValue` | — | My final grade in a course |
| `GET /d2l/api/le/{v}/grades/final/values/myGradeValues/` | `orgUnitIdsCSV` (max 100) | **Final grades across courses** |
| `GET /d2l/api/le/{v}/grades/courseCompletion/{userId}/` | `startExpiry`, `endExpiry`, `bookmark` | My completion records |

**Grade value response:**
```json
{
  "UserId": 123456,
  "OrgUnitId": 78901,
  "GradeObjectIdentifier": "9876",
  "GradeObjectName": "Midterm Exam",
  "GradeObjectType": 1,
  "GradeObjectTypeName": "Numeric",
  "DisplayedGrade": "85 / 100",
  "PointsNumerator": 85.0,
  "PointsDenominator": 100.0,
  "WeightedNumerator": null,
  "WeightedDenominator": null,
  "GradeObjectCategoryId": 5,
  "Comments": { "Text": "", "Html": "" }
}
```

### Grade Metadata

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/` | All grade objects (columns) in a course |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/{gradeObjectId}` | Specific grade object definition |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/categories/` | All grade categories |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/categories/{categoryId}` | Specific category |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/schemes/` | Grading schemes (letter grade mappings) |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/schemes/{gradeSchemeId}` | Specific scheme |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/setup/` | Grade configuration (calculation method, etc.) |
| `GET /d2l/api/le/{v}/{orgUnitId}/grades/{gradeObjectId}/statistics` | Statistics (min, max, avg, median, std dev) — if instructor shares |

> Grade object types: `Numeric`, `PassFail`, `SelectBox`, `Text`

---

## 6. Assignments / Dropbox

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/` | `onlyCurrentStudentsAndGroups` | All assignment folders |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}` | — | Folder details |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/submissions/mysubmissions/` | — | **My submissions** |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/submissions/{submissionId}/files/{fileId}` | — | Download submission file |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/feedback/{entityType}/{entityId}` | — | **Feedback on my submission** |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/feedback/{entityType}/{entityId}/attachments/{fileId}` | — | Download feedback file |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/feedback/{entityType}/{entityId}/links/{linkId}` | — | Feedback media link |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/{folderId}/attachments/{fileId}` | — | Download folder attachment (instructions file) |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/categories/` | — | Assignment categories |
| `GET /d2l/api/le/{v}/{orgUnitId}/dropbox/categories/{categoryId}` | — | Category with its folders |

> `entityType` is `user` or `group`. `entityId` is your userId or groupId.

**Folder response:**
```json
{
  "Id": 5555,
  "CategoryId": null,
  "Name": "Research Paper Draft",
  "CustomInstructions": { "Text": "Submit your 5-page draft...", "Html": "..." },
  "Attachments": [{ "FileId": 1, "FileName": "rubric.pdf", "Size": 1024 }],
  "DueDate": "2026-03-20T04:59:59.000Z",
  "Availability": { "StartDate": "...", "EndDate": "..." },
  "Assessment": { "ScoreDenominator": 100.0, "Rubrics": [] },
  "IsHidden": false,
  "SubmissionType": 0,
  "GradeItemId": 456,
  "IsAnonymous": false,
  "DropboxType": 0,
  "CompletionType": 0
}
```

---

## 7. Quizzes

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/` | — | All quizzes |
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/{quizId}` | — | Quiz details (name, instructions, time limit, attempts allowed, dates) |
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/{quizId}/attempts/` | `userId` | Quiz attempts (filter to own) |
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/{quizId}/attempts/{attemptId}` | — | Specific attempt details |
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/categories/` | — | Quiz categories |
| `GET /d2l/api/le/{v}/{orgUnitId}/quizzes/categories/{categoryId}` | — | Specific category |

> Students **cannot** enumerate quiz questions outside an active attempt. `/questions/` is instructor-only.

**QuizReadData response:**
```json
{
  "QuizId": 4444,
  "Name": "Chapter 3 Quiz",
  "IsActive": true,
  "GradeItemId": 9988,
  "Instructions": { "Text": "Complete all questions...", "Html": "" },
  "StartDate": "2026-03-01T13:00:00.000Z",
  "EndDate": "2026-03-08T23:59:00.000Z",
  "DueDate": "2026-03-08T23:59:00.000Z",
  "DisplayInCalendar": true,
  "NumberOfAttemptsAllowed": 1,
  "TimeLimitValue": 30
}
```

---

## 8. Discussions

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/` | — | All forums |
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/{forumId}` | — | Forum details |
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/{forumId}/topics/` | — | Topics in forum |
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/{forumId}/topics/{topicId}` | — | Topic details |
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/{forumId}/topics/{topicId}/posts/` | `pageSize`, `pageNumber`, `threadsOnly`, `threadId`, `sort` | Posts in topic |
| `GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/{forumId}/topics/{topicId}/posts/{postId}` | — | Specific post |
| `GET .../posts/{postId}/ReadStatus` | — | Read/unread status |
| `GET .../posts/{postId}/Flag` | — | Flagged status |
| `GET .../posts/{postId}/Rating` | — | Aggregate ratings |
| `GET .../posts/{postId}/Rating/MyRating` | — | My rating |
| `GET .../posts/{postId}/Votes` | — | Vote counts |
| `GET .../posts/{postId}/Votes/MyVote` | — | My vote |
| `GET .../topics/{topicId}/groupRestrictions/` | — | Group restrictions |

> Posts use page-number pagination (`?pageSize=20&pageNumber=1`), not bookmarks. `?threadsOnly=true` for top-level threads only.

---

## 9. Calendar & Events

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/calendar/events/myEvents/` | `association`, `eventType`, `orgUnitIdsCSV`, `startDateTime`, `endDateTime` | **Events across all courses** |
| `GET /d2l/api/le/{v}/{orgUnitId}/calendar/events/myEvents/` | `association`, `eventType`, `startDateTime`, `endDateTime` | Events for one course |
| `GET /d2l/api/le/{v}/calendar/events/myEvents/itemCounts/` | same | Event counts by org unit |
| `GET /d2l/api/le/{v}/{orgUnitId}/calendar/events/myEvents/itemCount` | same | Event count for one course |
| `GET /d2l/api/le/{v}/{orgUnitId}/calendar/event/{eventId}` | — | Specific event |
| `GET /d2l/api/le/{v}/{orgUnitId}/calendar/events/` | `associatedEventsOnly` | All events in course |
| `GET /d2l/api/le/{v}/{orgUnitId}/calendar/events/orgunits/` | `orgUnitIdsCSV`, `startDateTime`, `endDateTime`, `bookmark` | Events across multiple orgs (paged) |

> `eventType`: `1`=Assignment, `2`=Quiz, `3`=Discussion, `4`=Module, `5`=Custom.
> `association`: `0`=All, `1`=AssociatedWithContent, `2`=NotAssociatedWithContent.
> All datetimes are UTC ISO 8601: `2026-03-15T00:00:00.000Z`

---

## 10. News / Announcements

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/news/` | `since` | News items in a course |
| `GET /d2l/api/le/{v}/{orgUnitId}/news/{newsItemId}` | — | Specific news item |
| `GET /d2l/api/le/{v}/{orgUnitId}/news/{newsItemId}/attachments/{fileId}` | — | Download attachment |
| `GET /d2l/api/le/{v}/news/user/{userId}/` | `since`, `until` | News for user across courses |
| `GET /d2l/api/lp/{v}/feed/` | `since`, `until` | **Aggregated activity feed** (grades, news, etc.) |

---

## 11. Updates

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/updates/myUpdates` | Update counts in one course (new messages, grades, etc.) |
| `GET /d2l/api/le/{v}/updates/myUpdates/` | Update counts across all courses |

---

## 12. Awards / Badges

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/bas/{v}/associations/availableToEarn/` | `orgUnitId`, `awardType`, `limit`, `offset`, `search` | Awards available + already earned |
| `GET /d2l/api/bas/{v}/issued/users/{userId}/` | `orgUnitId`, `awardType`, `limit`, `offset`, `includeExpired`, `search` | Awards issued to me |
| `GET /d2l/api/bas/{v}/issued/certificates/{certificateId}` | — | Certificate details |
| `GET /d2l/api/bas/{v}/issued/certificates/{issuedId}/pdf` | — | **Download certificate PDF** |
| `GET /d2l/api/bas/{v}/creditSummary` | `orgUnitId`, `awardType`, `includeExpired` | Total award credit summary |
| `GET /d2l/api/bas/{v}/awards/` | `awardType`, `limit`, `offset`, `search` | All available awards |
| `GET /d2l/api/bas/{v}/awards/{awardId}` | — | Award details |

---

## 13. Checklists

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/` | All checklists |
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/{checklistId}` | Specific checklist |
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/{checklistId}/categories/` | Categories |
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/{checklistId}/categories/{categoryId}` | Specific category |
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/{checklistId}/items/` | Items |
| `GET /d2l/api/le/{v}/{orgUnitId}/checklists/{checklistId}/items/{checklistItemId}` | Specific item |

---

## 14. Surveys

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/` | All surveys |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/{surveyId}` | Survey details |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/{surveyId}/questions/` | Survey questions |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/{surveyId}/attempts/` | Survey attempts (`?userId=` filter) |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/{surveyId}/attempts/{attemptId}` | Specific attempt |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/categories/` | Survey categories |
| `GET /d2l/api/le/{v}/{orgUnitId}/surveys/categories/{categoryId}` | Specific category |

---

## 15. Groups & Sections

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/{orgUnitId}/groupcategories/` | Group categories |
| `GET /d2l/api/lp/{v}/{orgUnitId}/groupcategories/{groupCategoryId}` | Specific category |
| `GET /d2l/api/lp/{v}/{orgUnitId}/groupcategories/{groupCategoryId}/groups/` | Groups in category (with enrollments) |
| `GET /d2l/api/lp/{v}/{orgUnitId}/groupcategories/{groupCategoryId}/groups/{groupId}` | Specific group |
| `GET /d2l/api/lp/{v}/{orgUnitId}/groupcategories/{groupCategoryId}/groups/{groupId}/enrollments` | Group members |
| `GET /d2l/api/lp/{v}/{orgUnitId}/sections/mysections/` | **My sections** |
| `GET /d2l/api/lp/{v}/{orgUnitId}/sections/{sectionId}` | Section details |

---

## 16. Rubrics & Assessments

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/rubrics` | `objectType`, `objectId` | Rubrics on an object (e.g. assignment) |
| `GET /d2l/api/le/{v}/{orgUnitId}/assessment` | `assessmentType`, `objectType`, `objectId`, `rubricId`, `userId` | My rubric assessment/score |

> `objectType` values: `dropbox`, `quiz`, `discussion`

---

## 17. Lockers

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/locker/myLocker/{path}` | Browse/download personal locker (folder=JSON listing, file=stream) |
| `GET /d2l/api/le/{v}/{orgUnitId}/locker/group/{groupId}/{path}` | Browse/download group locker |

---

## 18. ePortfolio

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/eP/{v}/objects/my/` | `c`, `q`, `bookmark`, `pagesize` | My portfolio objects |
| `GET /d2l/api/eP/{v}/objects/shared/` | same | Objects shared with me |
| `GET /d2l/api/eP/{v}/objects/my/shared/modified/` | — | My objects modified by others |
| `GET /d2l/api/eP/{v}/object/{objectId}` | — | Specific object |
| `GET /d2l/api/eP/{v}/object/{objectId}/content` | — | Object file content |
| `GET /d2l/api/eP/{v}/object/{objectId}/associations/` | — | Associated objects |
| `GET /d2l/api/eP/{v}/object/{objectId}/shares/` | — | Active shares |
| `GET /d2l/api/eP/{v}/object/{objectId}/tags/` | — | Tags |
| `GET /d2l/api/eP/{v}/object/{objectId}/comments/` | — | Comments |
| `GET /d2l/api/eP/{v}/collection/{objectId}` | — | Collection |
| `GET /d2l/api/eP/{v}/collection/{objectId}/contents/` | — | Collection items |
| `GET /d2l/api/eP/{v}/presentation/{objectId}` | — | Presentation |
| `GET /d2l/api/eP/{v}/reflection/{objectId}` | — | Reflection |
| `GET /d2l/api/eP/{v}/artifact/{objectId}` | — | Artifact details |
| `GET /d2l/api/eP/{v}/artifact/file/{objectId}` | — | Artifact file |
| `GET /d2l/api/eP/{v}/artifact/link/{objectId}` | — | Artifact link |
| `GET /d2l/api/eP/{v}/activity/my/` | — | My activity |
| `GET /d2l/api/eP/{v}/activity/shared/` | — | Shared activity |
| `GET /d2l/api/eP/{v}/dashboard/` | — | Dashboard |
| `GET /d2l/api/eP/{v}/newsfeed/` | — | Newsfeed |

---

## 19. Competencies & Outcomes

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/competencies/structure` | `parentObjectId`, `depth`, `pageSize`, `bookmark` | Competency hierarchy |
| `GET /d2l/api/le/{v}/{orgUnitId}/lo/outcomeSets/` | — | Learning outcome sets |
| `GET /d2l/api/le/{v}/{orgUnitId}/lo/outcomeSets/{outcomeSetId}` | — | Specific outcome set |

---

## 20. Notifications & Alerts

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/alerts/user/{userId}` | My alerts (`?category=` filter) |
| `GET /d2l/api/lp/{v}/notifications/instant/carriers/` | Notification channels (email, SMS, etc.) |
| `GET /d2l/api/lp/{v}/notifications/instant/carriers/{carrierId}/subscriptions/users/{userId}/` | My subscriptions for a carrier |
| `GET /d2l/api/lp/{v}/notifications/instant/users/{userId}/settings` | My notification settings |

---

## 21. Accommodations

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/accommodations/{orgUnitId}/myaccommodations` | My accommodations (extra time, etc.) |

---

## 22. Classlist

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/{orgUnitId}/classlist/paged/` | `onlyShowShownInGrades`, `searchTerm`, `roleId` | Paged classlist |

> Fields: `Identifier`, `DisplayName`, `Username`, `Email`, `FirstName`, `LastName`, `RoleId`, `LastAccessed`, `IsOnline`

---

## 23. Account Settings & Locale

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/accountSettings/mySettings/locale/` | My locale settings |
| `GET /d2l/api/lp/{v}/locales/` | All available locales (paged) |
| `GET /d2l/api/lp/{v}/timezones/` | Available timezones |

---

## 24. Learning Repository

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/lr/{v}/repositories/all/` | — | List repositories |
| `GET /d2l/api/lr/{v}/objects/search/` | `query`, `offset`, `count`, `repositories` | Search learning objects |
| `GET /d2l/api/lr/{v}/objects/{objectId}/properties/` | — | Object properties |
| `GET /d2l/api/lr/{v}/objects/{objectId}/link/` | — | View URL |
| `GET /d2l/api/lr/{v}/objects/{objectId}/download/` | — | Download package |
| `GET /d2l/api/lr/{v}/objects/{objectId}/downloadfile/` | — | Download file |

---

## 25. LTI Links

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/le/{v}/lti/link/{orgUnitId}/` | LTI 1.x links in a course |
| `GET /d2l/api/le/{v}/lti/link/{orgUnitId}/{ltiLinkId}` | Specific link |
| `GET /d2l/api/le/{v}/ltiadvantage/links/orgunit/{orgUnitId}/` | LTI 1.3 links |
| `GET /d2l/api/le/{v}/ltiadvantage/links/orgunit/{orgUnitId}/{linkId}` | Specific LTI 1.3 link |

---

## 26. Widgets & Tools

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/lp/{v}/{orgUnitId}/widgetdata/{customWidgetId}/mydata` | My custom widget data |
| `GET /d2l/api/lp/{v}/tools/orgUnits/{orgUnitId}/toolNames` | Tool IDs and names in a course |

---

## 27. CPD Records (Continuing Professional Development)

| Endpoint | Params | Description |
|----------|--------|-------------|
| `GET /d2l/api/le/{v}/cpd/record/user/{userId}` | `methodId`, `categoryId`, `recordName`, `startDate`, `endDate`, `limit` | My CPD records |
| `GET /d2l/api/le/{v}/cpd/record/{recordId}` | — | Specific record |
| `GET /d2l/api/le/{v}/cpd/record/{recordId}/attachment/{attachmentId}` | — | Record attachment |
| `GET /d2l/api/le/{v}/cpd/target/progress/user/{userId}` | `methodId`, `categoryId`, `startDate`, `endDate` | Progress against targets |
| `GET /d2l/api/le/{v}/cpd/category/{categoryId}` | — | Category metadata |
| `GET /d2l/api/le/{v}/cpd/method/{methodId}` | — | Method metadata |
| `GET /d2l/api/le/{v}/cpd/question/{questionId}` | — | Question metadata |

---

## 28. API Metadata

| Endpoint | Description |
|----------|-------------|
| `GET /d2l/api/versions/` | All supported product versions |
| `GET /d2l/api/{productCode}/versions/` | Versions for one product |
| `GET /d2l/api/{productCode}/versions/{version}` | Check if version is supported |

---

## CLI Workflows

### "What's due this week?"
```
GET /d2l/api/le/{v}/content/myItems/due/?orgUnitIdsCSV=...&startDateTime=...&endDateTime=...
GET /d2l/api/le/{v}/overdueItems/myItems
GET /d2l/api/le/{v}/calendar/events/myEvents/?startDateTime=...&endDateTime=...
```

### "How am I doing in [course]?"
```
GET /d2l/api/le/{v}/{orgUnitId}/grades/values/myGradeValues/
GET /d2l/api/le/{v}/{orgUnitId}/grades/final/values/myGradeValue
GET /d2l/api/le/{v}/{orgUnitId}/grades/{gradeObjectId}/statistics
```

### "What's new?"
```
GET /d2l/api/le/{v}/updates/myUpdates/
GET /d2l/api/le/{v}/{orgUnitId}/news/
GET /d2l/api/lp/{v}/feed/
```

### "Full dump for AI assistant"
```
GET /d2l/api/lp/{v}/users/whoami
GET /d2l/api/lp/{v}/enrollments/myenrollments/?canAccess=true&isActive=true
  for each course:
    GET /d2l/api/le/{v}/{orgUnitId}/grades/values/myGradeValues/
    GET /d2l/api/le/{v}/{orgUnitId}/dropbox/folders/
    GET /d2l/api/le/{v}/{orgUnitId}/content/toc
    GET /d2l/api/le/{v}/{orgUnitId}/news/
    GET /d2l/api/le/{v}/{orgUnitId}/quizzes/
    GET /d2l/api/le/{v}/{orgUnitId}/discussions/forums/
GET /d2l/api/le/{v}/content/myItems/due/
GET /d2l/api/le/{v}/overdueItems/myItems
```

---

## Gotchas

1. **File downloads return raw streams, not JSON.** Topic files, submission files, locker files — stream bytes to disk.
2. **Bookmark pagination is sequential.** No random page access. Walk with `Bookmark` token.
3. **Discussion posts use page-number pagination** (`pageNumber`/`pageSize`), not bookmarks.
4. **Grade objects vs grade values.** Objects = column definitions. Values = actual scores.
5. **Quiz questions are instructor-only.** Students can't enumerate questions via API outside an active attempt.
6. **Release conditions are invisible.** Content just won't appear — no error, no 403.
7. **`canAccess=true`** on `myenrollments/` filters to currently accessible courses. Use it.
8. **All datetime params are UTC ISO 8601:** `2026-03-15T00:00:00.000Z`
9. **Rate limiting:** HTTP 429 with `Retry-After` header. Batch where possible (`orgUnitIdsCSV`).
10. **Separate products:** ePortfolio=`eP`, Awards=`bas`, LOR=`lr` — different path roots from `lp`/`le`.
11. **Module structure `Type`:** `0`=sub-module, `1`=topic. Topic `TopicType`: `1`=File, `2`=Link.
