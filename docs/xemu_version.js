export class XemuVersion {
  constructor(version_obj) {
    this.major = version_obj.major;
    this.minor = version_obj.minor;
    this.patch = version_obj.patch;
    this.build = version_obj.build;
    this.branch = version_obj.branch;
    this.git_hash = version_obj.git_hash;
    this.build_type = version_obj.build_type;
    this.short_name = version_obj.short;
    this.compare_name = version_obj.compare;
    this.friendlyName = null;

    if (!this.short_name || !this.compare_name) {
      console.error(`Invalid version object ${version_obj}`);
      throw new Error("Invalid version object");
    }
  }

  setTag(associatedTag) {
    this.friendlyName = associatedTag;
    this.compare_name = associatedTag;
    this.short_name = associatedTag;
  }

  toString() {
    return this.short_name;
  }

  localeCompare(other) {
    return this.compare_name.localeCompare(other.compare_name);
  }
}