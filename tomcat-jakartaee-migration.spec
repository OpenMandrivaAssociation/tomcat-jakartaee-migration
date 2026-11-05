Name:		tomcat-jakartaee-migration
Version:	1.0.13
Release:	1
Summary:	Tool that rewrites Java EE applications for Jakarta EE
Group:		Development/Java
License:	ASL 2.0
URL:		https://tomcat.apache.org/download-migration.cgi
Source0:	https://github.com/apache/tomcat-jakartaee-migration/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	mvn(org.apache.bcel:bcel)
BuildRequires:	mvn(org.apache.commons:commons-compress)
BuildRequires:	mvn(commons-io:commons-io)
BuildRequires:	python
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven
BuildOption(install):	--file-name jakartaee-migration --link %{name} --alias org.apache.tomcat:jakartaee-migration

%description
Rewrites a Java EE web application to the Jakarta EE package names. Tomcat
embeds this library. The jar is not shaded: its dependencies stay separate
system jars. OSGi manifest rewriting and the Ant task are omitted.

%prep
%setup -q -n %{name}-%{version}
rm -f src/main/java/org/apache/tomcat/jakartaee/ManifestConverter.java
# The Ant task is a frontend. Tomcat embeds Migration, and the system Ant
# package does not provide a Maven coordinate.
rm -f src/main/java/org/apache/tomcat/jakartaee/AntHandler.java \
	src/main/java/org/apache/tomcat/jakartaee/MigrationTask.java \
	src/test/java/org/apache/tomcat/jakartaee/AntHandlerTest.java \
	src/test/java/org/apache/tomcat/jakartaee/MigrationTaskTest.java
python - <<'PY'
import re
from pathlib import Path

migration = Path("src/main/java/org/apache/tomcat/jakartaee/Migration.java")
text = migration.read_text()
old = "        converters.add(new ManifestConverter());\n"
if old not in text:
    raise SystemExit("ManifestConverter call site missing")
migration.write_text(text.replace(old, "", 1))

pom = Path("pom.xml")
text = pom.read_text()
text, count = re.subn(
    r"\s*<parent>.*?</parent>",
    "\n",
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("parent missing")
text, count = re.subn(
    r"\s*<dependency>\s*<groupId>org\.apache\.ant</groupId>\s*<artifactId>ant</artifactId>.*?</dependency>",
    "\n",
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("ant dependency missing")
text, count = re.subn(
    r"\s*<dependency>\s*<groupId>org\.eclipse\.platform</groupId>\s*<artifactId>org\.eclipse\.osgi</artifactId>.*?</dependency>",
    "\n",
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit("osgi dependency missing")

def drop_plugins(text, artifact):
    needle = f"<artifactId>{artifact}</artifactId>"
    while True:
        start = text.find(needle)
        if start < 0:
            return text
        plugin = text.rfind("<plugin>", 0, start)
        end = text.find("</plugin>", start)
        if plugin < 0 or end < 0:
            raise SystemExit(f"plugin block broken for {artifact}")
        text = text[:plugin] + text[end + len("</plugin>"):]

# These stay on the sysjar keep list, so an uninstalled-plugin drop will not
# remove them. Shade would bundle dependencies, antrun signs test jars, and
# assembly builds a distribution we do not ship.
for artifact in ("maven-shade-plugin", "maven-antrun-plugin", "maven-assembly-plugin"):
    text = drop_plugins(text, artifact)
pom.write_text(text)
PY

%files -f .mfiles
%doc LICENSE.txt NOTICE.txt README.md
