"""
Pre-built prompt templates for weekend mode (comprehensive development and maintenance).
"""

def documentation_update_prompt(repo_name: str, repo_path: str, files_to_update: dict) -> str:
    """Generate prompt for updating CLAUDE.md and Architecture.md files"""
    file_list = "\n".join([
        f"- {filename}: {description}" 
        for filename, description in files_to_update.items()
    ])
    
    return f"""# Weekend Mode: Documentation Updates

You are updating documentation files in {repo_name} located at {repo_path}.
This is weekend mode - you can make direct changes and create PRs.

## Files to Update:
{file_list}

## Documentation Update Process:

### 1. CLAUDE.md Updates
If CLAUDE.md needs updating:
- Review current codebase structure and patterns
- Update project overview and architecture guidance
- Add new development commands if any were added
- Update configuration patterns
- Add any new integration points
- Ensure all sections are current and accurate

### 2. Architecture.md Updates  
If Architecture.md needs updating:
- Document new components and their relationships
- Update dependency diagrams and API descriptions
- Add new external integrations
- Document security considerations
- Update performance characteristics
- Add deployment architecture changes

### 3. Implementation Steps:
1. **Analyze Current State**:
   - Read existing documentation files
   - Compare with actual codebase structure
   - Identify gaps or outdated information

2. **Update Content**:
   - Make comprehensive updates to match current state
   - Add missing sections for new features
   - Remove references to deprecated features
   - Ensure consistency across all documentation

3. **Create PR**:
   - Create a new branch for documentation updates
   - Commit changes with clear messages
   - Create PR with detailed description of what was updated
   - Include before/after summaries

## Quality Guidelines:
- Use clear, concise language
- Include code examples where appropriate
- Maintain consistent formatting
- Cross-reference related sections
- Ensure accuracy with current implementation

## PR Description Template:
```
## Documentation Updates

### Files Updated:
- CLAUDE.md: [describe changes]
- Architecture.md: [describe changes]

### Key Changes:
- [List major updates]
- [New sections added]
- [Deprecated information removed]

### Impact:
- Improved developer onboarding
- Better architectural understanding
- Up-to-date project guidance
```

Create comprehensive, accurate documentation that will help future developers understand and work with this codebase effectively.
"""


def dependency_security_prompt(repo_name: str, repo_path: str, vulnerabilities: dict, dependency_files: dict) -> str:
    """Generate prompt for fixing dependency vulnerabilities and updates"""
    vuln_count = vulnerabilities.get('total_issues', 0)
    dep_files = "\n".join([
        f"- {filename}: {info['description']}"
        for filename, info in dependency_files.items()
    ])
    
    return f"""# Weekend Mode: Dependency Security & Updates

You are updating dependencies and fixing security vulnerabilities in {repo_name} located at {repo_path}.
This is weekend mode - you can make breaking changes and create comprehensive PRs.

## Current Status:
- **Security Issues**: {vuln_count} vulnerabilities detected
- **Dependency Files**: {len(dependency_files)} files found

## Dependency Files in Repository:
{dep_files}

## Security & Dependency Update Process:

### 1. Security Vulnerability Fixes (PRIORITY)
1. **Analyze Vulnerabilities**:
   - Review each security advisory
   - Understand the impact and severity
   - Identify affected code paths

2. **Update Vulnerable Dependencies**:
   - Update to patched versions
   - Test that functionality still works
   - Run security scans to verify fixes

3. **Code Changes if Needed**:
   - Update code that uses deprecated APIs
   - Fix breaking changes from dependency updates
   - Ensure all tests pass

### 2. General Dependency Updates
1. **Check for Updates**:
   - Identify outdated dependencies
   - Review changelog for breaking changes
   - Prioritize security and bug fix updates

2. **Update Strategy**:
   - Update patch versions first (safest)
   - Then minor versions with testing
   - Major versions in separate PRs

3. **Testing After Updates**:
   - Run full test suite
   - Check that builds complete successfully
   - Verify application starts and core functionality works

### 3. Major Framework Upgrades (if applicable)
Look for opportunities to upgrade major frameworks:

**For Java Projects**:
- SpringBoot major version upgrades
- Update Java version if needed
- Update Maven/Gradle plugins

**For Node.js Projects**:
- Angular major version upgrades
- React major version upgrades
- Update Node.js version if needed

**For Python Projects**:
- Django/Flask major version upgrades
- Update Python version if needed
- Update development tools

### 4. Implementation Guidelines:
1. **Create Separate PRs** for different types of updates:
   - Security fixes (urgent)
   - Patch/minor updates (safe)
   - Major upgrades (breaking)

2. **Test Thoroughly**:
   - Run automated tests
   - Test critical user paths manually
   - Check for performance regressions

3. **Document Changes**:
   - Update README with new requirements
   - Document breaking changes
   - Update deployment instructions if needed

## Commands to Use:
```bash
# Check for vulnerabilities (varies by language)
npm audit                    # Node.js
pip-audit                   # Python
./gradlew dependencyCheck   # Java
bundle audit                # Ruby

# Update dependencies
npm update                  # Node.js
pip install -U -r requirements.txt  # Python
./gradlew dependenciesUpdate  # Java
bundle update               # Ruby

# Security-specific updates
npm audit fix               # Node.js automatic fixes
```

## PR Description Template:
```
## Dependency Security & Updates

### Security Fixes:
- [List vulnerabilities fixed]
- [Severity levels addressed]

### Dependency Updates:
- [List major updates]
- [Breaking changes handled]

### Testing:
- [ ] All tests pass
- [ ] Application builds successfully
- [ ] Core functionality verified
- [ ] Security scan shows no new issues

### Breaking Changes:
- [List any breaking changes]
- [Migration steps if needed]
```

Focus on security first, then stability. Make sure all changes are thoroughly tested before creating PRs.
"""


def test_coverage_prompt(repo_name: str, repo_path: str, coverage_info: dict) -> str:
    """Generate prompt for improving test coverage and creating missing tests"""
    return f"""# Weekend Mode: Test Coverage Improvement

You are improving test coverage in {repo_name} located at {repo_path}.
This is weekend mode - you can create comprehensive test suites and refactor for testability.

## Current Test Status:
{coverage_info.get('summary', 'Coverage analysis needed')}

## Test Coverage Improvement Process:

### 1. Analyze Current Coverage
1. **Run Coverage Analysis**:
   ```bash
   # Examples for different languages
   npm run test:coverage      # Node.js/Jest
   pytest --cov=.            # Python
   ./gradlew jacocoTestReport # Java
   ```

2. **Identify Gaps**:
   - Find untested functions/methods
   - Look for missing edge case tests
   - Identify integration test gaps

### 2. Create Missing Unit Tests
Focus on:
1. **Critical Business Logic**:
   - Core algorithms and calculations
   - Data validation functions
   - Error handling paths

2. **Utility Functions**:
   - String/data manipulation
   - Configuration parsing
   - Helper methods

3. **Edge Cases**:
   - Null/undefined inputs
   - Empty collections
   - Boundary conditions
   - Error conditions

### 3. Integration Tests
Create tests for:
1. **API Endpoints**:
   - Happy path scenarios
   - Error responses
   - Authentication/authorization

2. **Database Operations**:
   - CRUD operations
   - Data consistency
   - Transaction handling

3. **External Dependencies**:
   - Mock external services
   - Test error handling
   - Verify retry logic

### 4. Test Quality Guidelines:
1. **Clear Test Names**:
   - Describe what is being tested
   - Include expected behavior
   - Mention specific conditions

2. **Proper Setup/Teardown**:
   - Initialize test data
   - Clean up after tests
   - Use test fixtures appropriately

3. **Isolated Tests**:
   - Tests should not depend on each other
   - Use mocks for external dependencies
   - Avoid shared state

### 5. Refactoring for Testability:
If code is hard to test:
1. **Extract Pure Functions**:
   - Separate business logic from side effects
   - Make functions more predictable
   - Reduce dependencies

2. **Dependency Injection**:
   - Make dependencies configurable
   - Use interfaces/abstractions
   - Enable easier mocking

3. **Break Down Large Functions**:
   - Split complex functions into smaller ones
   - Each function should have single responsibility
   - Make intermediate steps testable

### 6. Testing Tools & Frameworks:
Use appropriate tools for your language:

**JavaScript/TypeScript**:
- Jest, Mocha, Jasmine for unit tests
- Supertest for API testing
- Cypress for E2E testing

**Python**:
- pytest for unit tests
- unittest.mock for mocking
- pytest-django for Django apps

**Java**:
- JUnit 5 for unit tests
- Mockito for mocking
- TestContainers for integration tests

### 7. Coverage Targets:
Aim for:
- **90%+ line coverage** for critical modules
- **80%+ overall coverage** as minimum
- **100% coverage** for utility functions
- **Focus on branch coverage**, not just line coverage

## Implementation Strategy:
1. **Start with Critical Paths**: Test the most important functionality first
2. **Low-Hanging Fruit**: Add tests for simple, pure functions
3. **Complex Logic**: Break down and test complex algorithms
4. **Error Handling**: Ensure all error paths are tested
5. **Integration Points**: Test interfaces between components

## PR Description Template:
```
## Test Coverage Improvements

### Tests Added:
- [Number] new unit tests
- [Number] new integration tests
- [Areas] covered that were previously untested

### Coverage Improvement:
- Before: [X]% coverage
- After: [Y]% coverage
- Critical paths now covered: [list]

### Refactoring for Testability:
- [Functions extracted]
- [Dependencies injected]
- [Complex functions simplified]

### Test Quality:
- [ ] All tests pass
- [ ] Tests are isolated and independent
- [ ] Good test names and documentation
- [ ] Appropriate use of mocks and fixtures
```

Focus on testing critical business logic and error paths. Quality is more important than quantity - write meaningful tests that will catch real bugs.
"""


def security_audit_prompt(repo_name: str, repo_path: str, security_files: dict) -> str:
    """Generate prompt for comprehensive security audit and fixes"""
    files_found = "\n".join([
        f"- {filename}: {info['description']}"
        for filename, info in security_files.items()
    ])
    
    return f"""# Weekend Mode: Security Audit & Fixes

You are performing a comprehensive security audit and implementing fixes in {repo_name} located at {repo_path}.
This is weekend mode - you can make significant security improvements and create PRs.

## Security Files Found:
{files_found}

## Comprehensive Security Audit Process:

### 1. Authentication & Authorization Audit
1. **JWT Token Validation**:
   - Verify JWT signature validation is implemented
   - Check token expiration handling
   - Ensure proper token revocation
   - Validate audience and issuer claims

2. **Session Management**:
   - Check for secure session handling
   - Verify session timeout settings
   - Ensure proper session invalidation
   - Check for session fixation protection

3. **Access Control**:
   - Review role-based access control (RBAC)
   - Check for privilege escalation vulnerabilities
   - Verify authorization checks on all endpoints
   - Ensure principle of least privilege

### 2. Input Validation & Sanitization
1. **SQL Injection Prevention**:
   - Use parameterized queries/prepared statements
   - Review all database interactions
   - Check for dynamic query construction

2. **Cross-Site Scripting (XSS) Prevention**:
   - Implement output encoding
   - Use Content Security Policy (CSP)
   - Validate and sanitize all user inputs

3. **Command Injection Prevention**:
   - Avoid system command execution with user input
   - Use safe alternatives to shell commands
   - Implement input whitelisting

### 3. Data Protection
1. **Encryption at Rest**:
   - Encrypt sensitive data in databases
   - Use proper encryption algorithms
   - Secure key management

2. **Encryption in Transit**:
   - Enforce HTTPS/TLS
   - Check TLS configuration
   - Verify certificate validation

3. **Sensitive Data Handling**:
   - Remove hardcoded secrets
   - Implement proper secret management
   - Avoid logging sensitive information

### 4. Security Headers & Configuration
1. **HTTP Security Headers**:
   ```
   - Content-Security-Policy
   - X-Frame-Options
   - X-Content-Type-Options
   - Strict-Transport-Security
   - X-XSS-Protection
   ```

2. **CORS Configuration**:
   - Proper origin validation
   - Minimal allowed methods
   - Credential handling

### 5. Dependency Security
1. **Known Vulnerabilities**:
   - Scan for vulnerable dependencies
   - Update to patched versions
   - Remove unnecessary dependencies

2. **Supply Chain Security**:
   - Verify package integrity
   - Use lock files
   - Monitor for malicious packages

### 6. Error Handling & Logging
1. **Secure Error Handling**:
   - Don't expose internal information
   - Implement proper error responses
   - Log security events

2. **Security Monitoring**:
   - Log authentication events
   - Monitor for suspicious activity
   - Implement alerting for security events

### 7. Common Security Issues to Check:

**Web Applications**:
- OWASP Top 10 vulnerabilities
- API security best practices
- File upload security
- Redirect/forward validation

**Infrastructure**:
- Container security
- Cloud service configuration
- Network security
- Secret management

**Code Level**:
- Buffer overflows (C/C++)
- Insecure deserialization
- Race conditions
- Integer overflows

### 8. Security Tools & Scanning:
Use automated tools where available:

```bash
# Static Analysis
bandit .                    # Python
eslint-plugin-security     # JavaScript
SpotBugs                   # Java
gosec                      # Go

# Dependency Scanning
npm audit                  # Node.js
safety check              # Python
./gradlew dependencyCheck  # Java

# Container Scanning
docker scan image:tag      # Docker
trivy image image:tag      # Trivy

# Web Application Testing
zap-baseline.py            # OWASP ZAP
nmap                       # Network scanning
```

### 9. Security Implementation Examples:

**JWT Validation (Node.js)**:
```javascript
const jwt = require('jsonwebtoken');

function verifyToken(token) {{
  try {{
    return jwt.verify(token, process.env.JWT_SECRET, {{
      audience: 'your-app',
      issuer: 'your-issuer',
      algorithms: ['HS256']
    }});
  }} catch (error) {{
    throw new Error('Invalid token');
  }}
}}
```

**SQL Injection Prevention (Python)**:
```python
# Good - Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# Bad - String concatenation
cursor.execute(f"SELECT * FROM users WHERE id = {{user_id}}")
```

### 10. Documentation & Compliance:
1. **Security Documentation**:
   - Update SECURITY.md file
   - Document security procedures
   - Create incident response plan

2. **Compliance Considerations**:
   - GDPR data protection
   - SOC 2 requirements
   - Industry-specific regulations

## PR Description Template:
```
## Security Audit & Fixes

### Security Issues Fixed:
- [List specific vulnerabilities addressed]
- [Severity levels: Critical/High/Medium/Low]

### Security Improvements:
- [Authentication/authorization enhancements]
- [Input validation improvements]
- [Security headers implemented]
- [Encryption/data protection measures]

### Testing:
- [ ] Security tests pass
- [ ] Vulnerability scans show improvement
- [ ] Penetration testing completed (if applicable)
- [ ] No new security warnings

### Compliance:
- [Regulatory requirements addressed]
- [Security documentation updated]
```

Focus on critical security vulnerabilities first. Implement defense in depth - multiple layers of security controls. Test all security implementations thoroughly.
"""


def performance_optimization_prompt(repo_name: str, repo_path: str, performance_issues: dict) -> str:
    """Generate prompt for performance analysis and optimization"""
    return f"""# Weekend Mode: Performance Optimization

You are analyzing and optimizing performance in {repo_name} located at {repo_path}.
This is weekend mode - you can make significant performance improvements and refactoring.

## Performance Optimization Process:

### 1. Performance Analysis
1. **Identify Bottlenecks**:
   ```bash
   # Profiling tools by language
   node --prof app.js          # Node.js profiling
   python -m cProfile script.py # Python profiling
   java -XX:+FlightRecorder    # Java profiling
   go tool pprof               # Go profiling
   ```

2. **Database Performance**:
   - Slow query analysis
   - Missing index identification
   - Query optimization
   - Connection pooling efficiency

3. **Application Performance**:
   - CPU-intensive operations
   - Memory usage patterns
   - I/O bottlenecks
   - Algorithm efficiency

### 2. Frontend Performance (if applicable)
1. **Loading Performance**:
   - Bundle size optimization
   - Code splitting
   - Lazy loading implementation
   - Image optimization

2. **Runtime Performance**:
   - React/Vue component optimization
   - DOM manipulation efficiency
   - Event handler optimization
   - Memory leak prevention

3. **Network Performance**:
   - API request optimization
   - Caching strategies
   - CDN utilization
   - Compression

### 3. Backend Performance
1. **API Optimization**:
   - Response time improvement
   - Pagination implementation
   - Batch operations
   - Caching layers

2. **Database Optimization**:
   ```sql
   -- Add indexes for slow queries
   CREATE INDEX idx_user_email ON users(email);
   
   -- Optimize queries
   EXPLAIN ANALYZE SELECT ...;
   ```

3. **Caching Implementation**:
   - Redis/Memcached integration
   - Application-level caching
   - Database query caching
   - CDN caching

### 4. Common Performance Improvements:

**Database**:
- Add missing indexes
- Optimize N+1 queries
- Implement connection pooling
- Use read replicas
- Optimize schema design

**Application Code**:
- Algorithm optimization (O(n²) → O(n log n))
- Memory usage optimization
- Async/await implementation
- Batch processing
- Object pooling

**Infrastructure**:
- Enable compression
- Optimize container resource allocation
- Load balancer configuration
- Auto-scaling setup

### 5. Language-Specific Optimizations:

**Node.js**:
- Use streaming for large data
- Implement clustering
- Optimize event loop usage
- Memory management

**Python**:
- Use appropriate data structures
- Implement caching decorators
- Optimize loops and comprehensions
- Consider NumPy for calculations

**Java**:
- JVM tuning
- Garbage collection optimization
- Connection pooling
- Concurrent programming

### 6. Monitoring & Metrics:
1. **Application Metrics**:
   - Response times
   - Throughput (requests/second)
   - Error rates
   - Resource utilization

2. **Database Metrics**:
   - Query execution times
   - Connection pool usage
   - Lock waits
   - Cache hit ratios

3. **Infrastructure Metrics**:
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network throughput

### 7. Performance Testing:
1. **Load Testing**:
   ```bash
   # Load testing tools
   ab -n 1000 -c 10 http://localhost/api/endpoint
   wrk -t12 -c400 -d30s http://localhost/
   artillery quick --count 10 --num 5 http://localhost/
   ```

2. **Stress Testing**:
   - Gradually increase load
   - Find breaking points
   - Test recovery behavior

3. **Benchmark Comparisons**:
   - Before/after measurements
   - Different implementation approaches
   - A/B testing for optimizations

### 8. Implementation Examples:

**Database Index Creation**:
```sql
-- Analyze slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Add appropriate indexes
CREATE INDEX CONCURRENTLY idx_orders_user_created 
ON orders(user_id, created_at);
```

**Caching Implementation (Redis)**:
```python
import redis
import json

cache = redis.Redis()

def get_user_data(user_id):
    cached = cache.get(f"user:{{user_id}}")
    if cached:
        return json.loads(cached)
    
    data = database.get_user(user_id)
    cache.setex(f"user:{{user_id}}", 3600, json.dumps(data))
    return data
```

**Async Processing (Node.js)**:
```javascript
// Parallel processing
const results = await Promise.all([
  fetchUserData(userId),
  fetchOrderHistory(userId),
  fetchPreferences(userId)
]);

// Streaming for large datasets
const stream = fs.createReadStream('large-file.csv')
  .pipe(csv())
  .pipe(transform(processRecord))
  .pipe(writeToDatabase());
```

### 9. Performance Budget:
Set performance targets:
- Page load time: < 2 seconds
- API response time: < 200ms
- Database query time: < 100ms
- Time to first byte: < 600ms
- Bundle size: < 250kb gzipped

### 10. Continuous Performance Monitoring:
1. **Automated Performance Tests**:
   - Include in CI/CD pipeline
   - Performance regression detection
   - Automated alerts

2. **Real User Monitoring (RUM)**:
   - Track actual user experience
   - Geographic performance variations
   - Device-specific performance

## PR Description Template:
```
## Performance Optimizations

### Performance Improvements:
- [Specific optimizations implemented]
- [Bottlenecks addressed]
- [Performance gains achieved]

### Metrics:
- Response time: [before] → [after]
- Throughput: [before] → [after]
- Resource usage: [before] → [after]
- Database query time: [before] → [after]

### Changes Made:
- [Database indexes added]
- [Caching implemented]
- [Algorithm optimizations]
- [Infrastructure improvements]

### Testing:
- [ ] Load tests show improvement
- [ ] No performance regressions
- [ ] All functionality still works
- [ ] Monitoring shows positive metrics
```

Focus on the biggest bottlenecks first. Measure before and after every optimization. Don't optimize prematurely - profile first, then optimize based on data.
"""


def compliance_reporting_prompt(repo_name: str, repo_path: str, report_types: list) -> str:
    """Generate prompt for creating compliance and status reports"""
    report_list = "\n".join([f"- {report_type}" for report_type in report_types])
    
    return f"""# Weekend Mode: Compliance & Status Reporting

You are generating compliance reports and status updates for {repo_name} located at {repo_path}.
This is weekend mode - you can generate comprehensive reports and create documentation.

## Reports to Generate:
{report_list}

## Compliance Reporting Process:

### 1. Security Compliance Report
Generate comprehensive security status:

1. **Vulnerability Assessment**:
   - Current security vulnerabilities
   - Risk levels and impact assessment
   - Remediation timeline and status
   - Dependencies security status

2. **Security Controls**:
   - Authentication mechanisms
   - Authorization controls
   - Data encryption status
   - Security monitoring capabilities

3. **Compliance Status**:
   - OWASP Top 10 compliance
   - Industry-specific requirements
   - Data protection compliance (GDPR, CCPA)
   - Security audit findings

### 2. Performance Report
Analyze and report on system performance:

1. **Performance Metrics**:
   - Response time analysis
   - Throughput measurements
   - Resource utilization
   - Error rate trends

2. **Performance Issues**:
   - Identified bottlenecks
   - Performance degradation trends
   - Capacity planning recommendations
   - Optimization opportunities

3. **SLA Compliance**:
   - Service level agreements status
   - Uptime analysis
   - Performance target achievement
   - Incident impact analysis

### 3. Test Coverage Report
Comprehensive testing status:

1. **Coverage Analysis**:
   ```bash
   # Generate coverage reports
   npm run test:coverage > coverage_report.txt
   pytest --cov=. --cov-report=html
   ./gradlew jacocoTestReport
   ```

2. **Coverage Metrics**:
   - Line coverage percentage
   - Branch coverage analysis
   - Function/method coverage
   - Critical path coverage

3. **Testing Quality**:
   - Test execution status
   - Test failure analysis
   - Test maintenance needs
   - Missing test scenarios

### 4. Dependency Analysis Report
Review project dependencies:

1. **Dependency Health**:
   - Outdated packages
   - Security vulnerabilities
   - License compliance
   - Maintenance status

2. **Update Recommendations**:
   - Critical security updates
   - Feature enhancement opportunities
   - Breaking change impacts
   - Update prioritization

### 5. Code Quality Report
Analyze code quality metrics:

1. **Static Analysis**:
   ```bash
   # Code quality tools
   eslint . --format json > eslint_report.json
   pylint --output-format=json src/ > pylint_report.json
   sonar-scanner
   ```

2. **Quality Metrics**:
   - Technical debt assessment
   - Code complexity analysis
   - Coding standard compliance
   - Maintainability index

### 6. Report Generation Tools:

**Use appropriate tools for data collection**:
```bash
# Security scanning
npm audit --json > security_audit.json
safety check --json > python_security.json

# Performance monitoring
curl -s "http://monitoring-api/metrics" > performance_data.json

# Code quality
sonar-scanner -Dsonar.projectKey=project > sonar_report.json
```

### 7. Report Format & Structure:

**Executive Summary Format**:
```markdown
# {{Repository}} Status Report - {{Date}}

## Executive Summary
- Overall health status: [Green/Yellow/Red]
- Critical issues: [Number]
- Key achievements: [List]
- Recommended actions: [Priority list]

## Security Status
- Vulnerabilities: [High: X, Medium: Y, Low: Z]
- Compliance status: [Percentage]
- Recent security improvements: [List]

## Performance Status  
- Average response time: [Xms]
- Uptime: [X%]
- Performance issues: [Count]
- Optimization opportunities: [List]

## Test Coverage
- Overall coverage: [X%]
- Critical path coverage: [X%]
- Missing tests: [Areas]

## Dependencies
- Total dependencies: [Count]
- Outdated: [Count]
- Security vulnerabilities: [Count]
- Recommended updates: [Priority list]

## Action Items
1. [Priority 1 items]
2. [Priority 2 items]
3. [Priority 3 items]
```

### 8. Automated Report Generation:
Create scripts for regular reporting:

```python
# Example report generation script
import json
import subprocess
from datetime import datetime

def generate_security_report():
    result = subprocess.run(['npm', 'audit', '--json'], 
                          capture_output=True, text=True)
    audit_data = json.loads(result.stdout)
    
    return {{
        'vulnerabilities': audit_data.get('metadata', {{}}).get('vulnerabilities', {{}}),
        'dependencies': audit_data.get('metadata', {{}}).get('dependencies', 0),
        'timestamp': datetime.now().isoformat()
    }}

def generate_coverage_report():
    result = subprocess.run(['npm', 'run', 'test:coverage'], 
                          capture_output=True, text=True)
    # Parse coverage output
    return parse_coverage_output(result.stdout)
```

### 9. Report Distribution:
1. **Stakeholder Reports**:
   - Executive summary for management
   - Technical details for development teams
   - Action items for project managers

2. **Automated Delivery**:
   - Email reports to stakeholders
   - Dashboard updates
   - Integration with project management tools

### 10. Trend Analysis:
Track metrics over time:
```python
def analyze_trends(current_report, historical_reports):
    trends = {{}}
    
    # Security trend
    current_vulns = current_report['security']['vulnerabilities']
    previous_vulns = historical_reports[-1]['security']['vulnerabilities']
    trends['security'] = calculate_trend(current_vulns, previous_vulns)
    
    # Performance trend
    current_perf = current_report['performance']['response_time']
    previous_perf = historical_reports[-1]['performance']['response_time']
    trends['performance'] = calculate_trend(current_perf, previous_perf)
    
    return trends
```

## Implementation Tasks:
1. **Data Collection**: Gather metrics from all relevant tools
2. **Report Generation**: Create comprehensive reports in markdown/HTML
3. **Trend Analysis**: Compare with historical data
4. **Action Item Creation**: Generate prioritized recommendations
5. **Distribution**: Send reports to appropriate stakeholders

## Output Requirements:
- Executive summary (1-2 pages)
- Detailed technical report
- Action item list with priorities
- Trend analysis charts (if possible)
- Raw data files for further analysis

Generate comprehensive, actionable reports that help stakeholders understand the current state and make informed decisions about improvements needed.
"""